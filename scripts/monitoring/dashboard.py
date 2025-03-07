#!/usr/bin/env python3
"""
Streamlit-Dashboard für die Visualisierung von API-Monitoring und Backup-Daten.

Dieses Skript erstellt ein interaktives Web-Dashboard zur Überwachung der API-Nutzung,
Kosten und Backups.

Verwendung:
    streamlit run scripts/monitoring/dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import altair as alt
import plotly.express as px
import plotly.graph_objects as go

from scripts.monitoring.api_monitor import APIMonitor
from scripts.monitoring.config import (
    MONITORING_DATA_DIR, DATA_DIR, MODEL_COSTS
)

# Seitenkonfiguration
st.set_page_config(
    page_title="API-Monitoring Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für besseres Aussehen
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .small-text {
        font-size: 0.8rem;
        color: #555;
    }
    .backup-card {
        background-color: #f9f9f9;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-left: 5px solid #4CAF50;
    }
    .backup-card.incremental {
        border-left: 5px solid #2196F3;
    }
    .backup-card h4 {
        margin-top: 0;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialisiere den API-Monitor
@st.cache_resource
def get_api_monitor():
    return APIMonitor()

monitor = get_api_monitor()

# Seitennavigation
st.sidebar.title("API-Monitoring Dashboard")
page = st.sidebar.radio(
    "Navigation",
    ["Übersicht", "API-Kosten", "Backups", "Einstellungen"]
)

# Lädt die Backup-Metadaten
@st.cache_data(ttl=60)  # Cache für 60 Sekunden
def load_backup_metadata():
    metadata = monitor._load_backup_metadata()
    backups = metadata.get('backups', [])
    
    if not backups:
        return pd.DataFrame()
        
    df = pd.DataFrame(backups)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    if 'size' in df.columns:
        df['size_mb'] = df['size'] / (1024 * 1024)
        
    return df

# Lädt die API-Nutzungsdaten
@st.cache_data(ttl=60)  # Cache für 60 Sekunden
def load_api_usage_data():
    try:
        with open(monitor.usage_file, 'r') as f:
            data = json.load(f)
            
        # Extrahiere die API-Aufrufe
        api_calls = data.get('api_calls', [])
        if not api_calls:
            return pd.DataFrame()
            
        df = pd.DataFrame(api_calls)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        return df
    except (IOError, json.JSONDecodeError):
        return pd.DataFrame()

# Dateigröße formatieren
def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

# Daten für die aktuelle Seite laden
api_usage_df = load_api_usage_data()
backups_df = load_backup_metadata()

# Datum formatieren
def format_date(dt):
    if pd.isna(dt):
        return "N/A"
    elif isinstance(dt, pd.Timestamp) or isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    else:
        return str(dt)

###################
# Übersichtsseite #
###################
if page == "Übersicht":
    st.title("📊 API-Monitoring Übersicht")
    
    # Metriken für die Übersicht
    col1, col2, col3, col4 = st.columns(4)
    
    # Total API-Kosten
    total_cost = monitor.data.get('total_cost', 0)
    budget_limit = monitor.budget_limit
    percentage_used = (total_cost / budget_limit) * 100 if budget_limit > 0 else 0
    
    with col1:
        st.metric(
            label="Gesamtkosten",
            value=f"${total_cost:.2f}",
            delta=f"{percentage_used:.1f}% des Budgets"
        )
    
    # Letzte API-Nutzung
    last_call_time = "Keine Daten" 
    if not api_usage_df.empty and 'timestamp' in api_usage_df.columns:
        last_call_time = format_date(api_usage_df['timestamp'].max())
        
    with col2:
        st.metric(
            label="Letzte API-Anfrage",
            value=last_call_time
        )
    
    # Backup-Status
    last_backup_date = "Keine Backups"
    if not backups_df.empty and 'date' in backups_df.columns:
        last_backup_date = format_date(backups_df['date'].max())
    
    with col3:
        st.metric(
            label="Letztes Backup",
            value=last_backup_date
        )
    
    # Anzahl der API-Aufrufe
    num_api_calls = len(api_usage_df) if not api_usage_df.empty else 0
    
    with col4:
        st.metric(
            label="API-Aufrufe",
            value=f"{num_api_calls}"
        )
    
    # Grafik: Kostenentwicklung über die Zeit
    st.subheader("Kostenentwicklung")
    
    if not api_usage_df.empty and 'timestamp' in api_usage_df.columns and 'cost' in api_usage_df.columns:
        # Kosten pro Tag aggregieren
        daily_costs = api_usage_df.copy()
        daily_costs['date'] = daily_costs['timestamp'].dt.date
        daily_costs = daily_costs.groupby('date')['cost'].sum().reset_index()
        daily_costs['date'] = pd.to_datetime(daily_costs['date'])
        daily_costs['cumulative_cost'] = daily_costs['cost'].cumsum()
        
        # Grafik mit Plotly erstellen
        fig = px.line(
            daily_costs, 
            x='date', 
            y='cumulative_cost',
            title='Kumulative API-Kosten',
            labels={'date': 'Datum', 'cumulative_cost': 'Gesamtkosten ($)'}
        )
        fig.add_hline(
            y=budget_limit, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Budget-Limit: ${budget_limit:.2f}"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine API-Nutzungsdaten verfügbar für die Kostenentwicklung.")
    
    # Grafik: Modellverteilung
    st.subheader("API-Nutzung nach Modell")
    
    if not api_usage_df.empty and 'model' in api_usage_df.columns:
        model_usage = api_usage_df['model'].value_counts().reset_index()
        model_usage.columns = ['model', 'count']
        
        fig = px.pie(
            model_usage, 
            values='count', 
            names='model',
            title='Verteilung der API-Aufrufe nach Modell'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine API-Nutzungsdaten verfügbar für die Modellverteilung.")

    # Backup-Übersicht
    st.subheader("Backup-Übersicht")
    
    if not backups_df.empty:
        # Anzahl der verschiedenen Backup-Typen
        if 'type' in backups_df.columns:
            backup_types = backups_df['type'].value_counts().reset_index()
            backup_types.columns = ['type', 'count']
            
            fig = px.bar(
                backup_types,
                x='type',
                y='count',
                title='Backup-Typen',
                labels={'type': 'Typ', 'count': 'Anzahl'},
                color='type',
                color_discrete_map={
                    'full': '#4CAF50',
                    'incremental': '#2196F3'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Neueste Backups anzeigen
        st.markdown("**Neueste Backups:**")
        latest_backups = backups_df.sort_values('date', ascending=False).head(3)
        
        for _, backup in latest_backups.iterrows():
            backup_type = backup.get('type', 'unbekannt')
            backup_date = format_date(backup.get('date'))
            backup_size = format_size(backup.get('size', 0))
            
            html_class = "backup-card"
            if backup_type == "incremental":
                html_class += " incremental"
                
            st.markdown(f"""
            <div class="{html_class}">
                <h4>{backup_date} ({backup_type})</h4>
                <p>Größe: {backup_size} | Gesamtkosten: ${backup.get('total_cost', 0):.2f}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Keine Backup-Daten verfügbar.")

##################
# API-Kostenseite #
##################
elif page == "API-Kosten":
    st.title("💰 API-Kosten-Analyse")
    
    # Gesamtstatus
    col1, col2 = st.columns(2)
    
    with col1:
        # Budget-Fortschritt
        total_cost = monitor.data.get('total_cost', 0)
        budget_limit = monitor.budget_limit
        percentage_used = (total_cost / budget_limit) * 100 if budget_limit > 0 else 0
        
        # Fortschrittsbalken für das Budget
        st.subheader(f"Budget-Nutzung: ${total_cost:.2f} / ${budget_limit:.2f}")
        
        # Farbe des Fortschrittsbalkens basierend auf der Nutzung
        color = "green"
        if percentage_used > 75:
            color = "orange"
        if percentage_used > 90:
            color = "red"
            
        st.progress(min(percentage_used / 100, 1.0), text=f"{percentage_used:.1f}%")
        
        if percentage_used > 90:
            st.warning("⚠️ Budget fast aufgebraucht!")
        elif percentage_used > 75:
            st.info("ℹ️ Budget über 75% genutzt")
    
    with col2:
        # Kostenverteilung nach Modellen
        if 'models' in monitor.data:
            models_data = []
            for model, stats in monitor.data['models'].items():
                if 'cost' in stats:
                    models_data.append({
                        'model': model,
                        'cost': stats['cost'],
                        'calls': stats.get('calls', 0)
                    })
            
            if models_data:
                models_df = pd.DataFrame(models_data)
                
                fig = px.pie(
                    models_df,
                    values='cost',
                    names='model',
                    title='Kostenverteilung nach Modell'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Detaillierte Analysen
    st.subheader("Detaillierte Kostenanalyse")
    
    # Tabs für verschiedene Ansichten
    tab1, tab2, tab3 = st.tabs(["Nach Modell", "Nach Aufgabe", "Einzelne API-Aufrufe"])
    
    with tab1:
        if 'models' in monitor.data:
            models_df = pd.DataFrame([
                {
                    'model': model,
                    'cost': stats.get('cost', 0),
                    'calls': stats.get('calls', 0),
                    'tokens_in': stats.get('tokens_in', 0),
                    'tokens_out': stats.get('tokens_out', 0),
                    'avg_cost_per_call': stats.get('cost', 0) / stats.get('calls', 1)
                }
                for model, stats in monitor.data['models'].items()
            ])
            
            if not models_df.empty:
                # Sortieren nach Kosten absteigend
                models_df = models_df.sort_values('cost', ascending=False)
                
                # Bar-Chart für Kosten nach Modell
                fig = px.bar(
                    models_df,
                    x='model',
                    y='cost',
                    color='model',
                    title='Kosten nach Modell',
                    labels={'model': 'Modell', 'cost': 'Kosten ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabelle mit allen Details
                st.dataframe(
                    models_df.style.format({
                        'cost': '${:.4f}',
                        'avg_cost_per_call': '${:.6f}'
                    }),
                    hide_index=True
                )
            else:
                st.info("Keine Daten zur Modellnutzung verfügbar.")
        else:
            st.info("Keine Daten zur Modellnutzung verfügbar.")
    
    with tab2:
        if 'tasks' in monitor.data:
            tasks_df = pd.DataFrame([
                {
                    'task': task,
                    'cost': stats.get('cost', 0),
                    'calls': stats.get('calls', 0),
                    'avg_cost_per_call': stats.get('cost', 0) / stats.get('calls', 1)
                }
                for task, stats in monitor.data['tasks'].items()
            ])
            
            if not tasks_df.empty:
                # Sortieren nach Kosten absteigend
                tasks_df = tasks_df.sort_values('cost', ascending=False)
                
                # Bar-Chart für Kosten nach Aufgabe
                fig = px.bar(
                    tasks_df,
                    x='task',
                    y='cost',
                    color='task',
                    title='Kosten nach Aufgabe',
                    labels={'task': 'Aufgabe', 'cost': 'Kosten ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabelle mit allen Details
                st.dataframe(
                    tasks_df.style.format({
                        'cost': '${:.4f}',
                        'avg_cost_per_call': '${:.6f}'
                    }),
                    hide_index=True
                )
            else:
                st.info("Keine Daten zur Aufgabennutzung verfügbar.")
        else:
            st.info("Keine Daten zur Aufgabennutzung verfügbar.")
    
    with tab3:
        if not api_usage_df.empty:
            # Füge formatierte Spalten hinzu
            api_display_df = api_usage_df.copy()
            if 'timestamp' in api_display_df.columns:
                api_display_df['timestamp'] = api_display_df['timestamp'].apply(format_date)
            
            # Zeige die neuesten Einträge zuerst
            api_display_df = api_display_df.sort_values('timestamp', ascending=False)
            
            # Formatiere die Kostenspalte
            if 'cost' in api_display_df.columns:
                api_display_df['cost'] = api_display_df['cost'].apply(lambda x: f"${x:.6f}")
            
            # Zeige die Tabelle an
            st.dataframe(api_display_df, hide_index=True)
        else:
            st.info("Keine API-Aufrufe gefunden.")
    
    # Kostenprognose
    st.subheader("Kostenprognose")
    
    if not api_usage_df.empty and 'timestamp' in api_usage_df.columns and 'cost' in api_usage_df.columns:
        # Berechne den durchschnittlichen täglichen Verbrauch
        api_usage_df['date'] = api_usage_df['timestamp'].dt.date
        daily_costs = api_usage_df.groupby('date')['cost'].sum().reset_index()
        
        if len(daily_costs) > 1:
            avg_daily_cost = daily_costs['cost'].mean()
            
            # Berechne Prognose
            days_to_budget_limit = (budget_limit - total_cost) / avg_daily_cost if avg_daily_cost > 0 else float('inf')
            estimated_depletion_date = datetime.now() + timedelta(days=days_to_budget_limit)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="Durchschnittliche tägliche Kosten",
                    value=f"${avg_daily_cost:.4f}"
                )
            
            with col2:
                if days_to_budget_limit < float('inf'):
                    st.metric(
                        label="Geschätztes Budgetende",
                        value=estimated_depletion_date.strftime("%Y-%m-%d")
                    )
                else:
                    st.metric(
                        label="Geschätztes Budgetende",
                        value="Nie (kein Verbrauch)"
                    )
            
            # Prognose-Chart
            if days_to_budget_limit < 90 and days_to_budget_limit > 0:
                # Erstelle Prognose für die nächsten 30 Tage oder bis zum Budgetende
                forecast_days = min(30, int(days_to_budget_limit) + 5)
                
                last_date = datetime.now().date()
                if not daily_costs.empty:
                    last_date = pd.to_datetime(daily_costs['date'].max()).date()
                
                forecast_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
                forecast_costs = [total_cost + (avg_daily_cost * i) for i in range(1, forecast_days + 1)]
                
                forecast_df = pd.DataFrame({
                    'date': forecast_dates,
                    'forecasted_cost': forecast_costs
                })
                
                fig = go.Figure()
                
                # Füge tatsächliche Kosten hinzu
                if 'cumulative_cost' in daily_costs.columns:
                    fig.add_trace(go.Scatter(
                        x=daily_costs['date'],
                        y=daily_costs['cumulative_cost'],
                        mode='lines+markers',
                        name='Tatsächliche Kosten'
                    ))
                
                # Füge Prognose hinzu
                fig.add_trace(go.Scatter(
                    x=forecast_df['date'],
                    y=forecast_df['forecasted_cost'],
                    mode='lines',
                    line=dict(dash='dash'),
                    name='Prognose'
                ))
                
                # Füge Budgetlinie hinzu
                fig.add_hline(
                    y=budget_limit, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"Budget-Limit: ${budget_limit:.2f}"
                )
                
                fig.update_layout(
                    title='Kostenprognose',
                    xaxis_title='Datum',
                    yaxis_title='Kumulative Kosten ($)'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                if days_to_budget_limit < 7:
                    st.warning(f"⚠️ Bei aktuellem Verbrauch wird das Budget in {days_to_budget_limit:.1f} Tagen aufgebraucht sein!")
                elif days_to_budget_limit < 14:
                    st.info(f"ℹ️ Bei aktuellem Verbrauch wird das Budget in {days_to_budget_limit:.1f} Tagen aufgebraucht sein.")
        else:
            st.info("Nicht genügend Daten für eine Kostenprognose.")
    else:
        st.info("Keine Daten für eine Kostenprognose verfügbar.")

###############
# Backupseite #
###############
elif page == "Backups":
    st.title("💾 Backup-Verwaltung")
    
    # Backup-Statistiken
    if not backups_df.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            num_backups = len(backups_df)
            st.metric(
                label="Anzahl Backups",
                value=num_backups
            )
        
        with col2:
            if 'type' in backups_df.columns:
                full_backups = backups_df[backups_df['type'] == 'full'].shape[0]
                incremental_backups = backups_df[backups_df['type'] == 'incremental'].shape[0]
                
                st.metric(
                    label="Vollständige Backups",
                    value=full_backups
                )
        
        with col3:
            if 'type' in backups_df.columns:
                st.metric(
                    label="Inkrementelle Backups",
                    value=incremental_backups
                )
        
        # Backup-Größenentwicklung
        st.subheader("Backup-Größen im Zeitverlauf")
        
        if 'date' in backups_df.columns and 'size_mb' in backups_df.columns:
            size_chart = alt.Chart(backups_df).mark_bar().encode(
                x=alt.X('date:T', title='Datum'),
                y=alt.Y('size_mb:Q', title='Größe (MB)'),
                color=alt.Color('type:N', title='Backup-Typ')
            ).properties(
                title='Backup-Größen'
            )
            
            st.altair_chart(size_chart, use_container_width=True)
        
        # Backup-Liste
        st.subheader("Alle Backups")
        
        # Sortiere nach Datum (neueste zuerst)
        backups_display = backups_df.sort_values('date', ascending=False).copy()
        
        # Formatiere die Spalten
        if 'date' in backups_display.columns:
            backups_display['date'] = backups_display['date'].apply(format_date)
        if 'size' in backups_display.columns:
            backups_display['formatted_size'] = backups_display['size'].apply(format_size)
        if 'total_cost' in backups_display.columns:
            backups_display['total_cost'] = backups_display['total_cost'].apply(lambda x: f"${x:.2f}")
        
        # Wähle die anzuzeigenden Spalten aus
        display_columns = ['date', 'type', 'formatted_size', 'total_cost']
        display_columns = [col for col in display_columns if col in backups_display.columns]
        
        if display_columns:
            st.dataframe(backups_display[display_columns], hide_index=True)
        else:
            st.dataframe(backups_display, hide_index=True)
        
        # Backup-Wiederherstellungsfunktion
        st.subheader("Backup-Wiederherstellung")
        
        backup_dates = backups_df['date'].dt.date.unique() if 'date' in backups_df.columns else []
        backup_dates = sorted(backup_dates, reverse=True)
        
        if backup_dates:
            backup_date_str = st.selectbox(
                "Wähle ein Backup-Datum für die Wiederherstellung:",
                options=[date.isoformat() for date in backup_dates]
            )
            
            if st.button("Backup wiederherstellen", type="primary"):
                with st.spinner("Stelle Backup wieder her..."):
                    success = monitor.restore_from_backup(specific_date=backup_date_str)
                    
                    if success:
                        st.success(f"Backup vom {backup_date_str} erfolgreich wiederhergestellt!")
                    else:
                        st.error(f"Fehler bei der Wiederherstellung des Backups vom {backup_date_str}.")
        else:
            st.info("Keine Backups verfügbar für die Wiederherstellung.")
    else:
        st.info("Keine Backup-Daten verfügbar.")
    
    # Backup-Integritätsprüfung
    st.subheader("Backup-Integritätsprüfung")
    
    if not backups_df.empty:
        # Checkbox für die Auswahl aller Backups
        check_all = st.checkbox("Alle Backups prüfen")
        
        # Multi-Select für die Auswahl bestimmter Backups
        backup_options = []
        if 'date' in backups_df.columns and 'type' in backups_df.columns:
            for _, row in backups_df.iterrows():
                option_text = f"{format_date(row['date'])} ({row['type']})"
                backup_options.append((option_text, row))
        
        selected_backups = []
        if check_all:
            selected_backups = [b[1] for b in backup_options]
        else:
            selected_options = st.multiselect(
                "Wähle Backups für die Integritätsprüfung:",
                options=[b[0] for b in backup_options]
            )
            
            for option in selected_options:
                for backup_option, backup_row in backup_options:
                    if option == backup_option:
                        selected_backups.append(backup_row)
        
        if selected_backups and st.button("Integritätsprüfung durchführen", type="primary"):
            with st.spinner("Prüfe Backup-Integrität..."):
                results = []
                
                for backup in selected_backups:
                    if 'file' in backup:
                        backup_file = monitor.backup_dir / backup['file']
                        is_valid = monitor._verify_backup_integrity(backup_file)
                        
                        results.append({
                            'date': format_date(backup['date']) if 'date' in backup else 'Unbekannt',
                            'type': backup.get('type', 'Unbekannt'),
                            'file': backup['file'],
                            'status': "✅ Gültig" if is_valid else "❌ Beschädigt"
                        })
                
                # Zeige die Ergebnisse an
                if results:
                    results_df = pd.DataFrame(results)
                    st.dataframe(results_df, hide_index=True)
                    
                    # Prüfe, ob beschädigte Backups existieren
                    damaged_backups = [r for r in results if "Beschädigt" in r['status']]
                    if damaged_backups:
                        st.error(f"{len(damaged_backups)} beschädigte Backups gefunden!")
                    else:
                        st.success("Alle Backups sind gültig!")
                else:
                    st.error("Keine Backups geprüft.")
    else:
        st.info("Keine Backup-Daten verfügbar für die Integritätsprüfung.")
    
    # Manuelles Backup erstellen
    st.subheader("Manuelles Backup erstellen")
    
    col1, col2 = st.columns(2)
    
    with col1:
        backup_type = st.radio("Backup-Typ", ["Vollständig", "Inkrementell"])
    
    with col2:
        if st.button("Backup jetzt erstellen", type="primary"):
            is_incremental = backup_type == "Inkrementell"
            
            with st.spinner(f"Erstelle {backup_type.lower()}es Backup..."):
                if is_incremental:
                    success = monitor._create_backup(incremental=True)
                else:
                    success = monitor._create_full_backup()
                
                if success:
                    today = datetime.now().date().isoformat()
                    backup_file = list(monitor.backup_dir.glob(f"*{today}*.json"))
                    
                    if backup_file:
                        backup_size = format_size(os.path.getsize(backup_file[0]))
                        st.success(f"{backup_type}es Backup erfolgreich erstellt! Größe: {backup_size}")
                    else:
                        st.success(f"{backup_type}es Backup erfolgreich erstellt!")
                    
                    # Aktualisiere die Metadaten
                    # (Dies sollte automatisch während der Backup-Erstellung geschehen)
                    
                    # Lade die Daten neu
                    st.rerun()
                else:
                    st.error(f"Fehler beim Erstellen des {backup_type.lower()}en Backups.")

###################
# Einstellungsseite #
###################
elif page == "Einstellungen":
    st.title("⚙️ Einstellungen")
    
    # Budget-Einstellungen
    st.subheader("Budget-Einstellungen")
    
    current_budget = monitor.budget_limit
    new_budget = st.number_input(
        "Budget-Limit (USD)",
        min_value=0.0,
        value=current_budget,
        step=5.0,
        format="%.2f"
    )
    
    # Warning-Schwellenwerte
    st.subheader("Warnschwellen")
    
    current_thresholds = monitor.warning_thresholds
    threshold_options = [25, 50, 75, 90, 95]
    
    selected_thresholds = st.multiselect(
        "Budget-Warnschwellen (%)",
        options=threshold_options,
        default=[t * 100 for t in current_thresholds]
    )
    
    # Backup-Einstellungen
    st.subheader("Backup-Einstellungen")
    
    current_max_backups = monitor.max_daily_backups
    new_max_backups = st.number_input(
        "Maximale Anzahl Backups",
        min_value=1,
        max_value=100,
        value=current_max_backups
    )
    
    # Speichern der Einstellungen
    if st.button("Einstellungen speichern", type="primary"):
        # Aktualisiere das Budget
        if new_budget != current_budget:
            monitor.budget_limit = new_budget
            monitor.data['budget_limit'] = new_budget
        
        # Aktualisiere die Warnschwellen
        if sorted(selected_thresholds) != sorted([t * 100 for t in current_thresholds]):
            monitor.warning_thresholds = [t / 100 for t in selected_thresholds]
            monitor._warnings_sent = {threshold: False for threshold in monitor.warning_thresholds}
        
        # Aktualisiere die maximale Anzahl an Backups
        if new_max_backups != current_max_backups:
            monitor.max_daily_backups = new_max_backups
        
        # Speichere die Aktualisierungen
        monitor._save_data()
        
        st.success("Einstellungen erfolgreich gespeichert!")
    
    # Restore aus Kontext-Informationen
    st.subheader("Kontext-Informationen")
    
    context_info = monitor.list_all_context_information()
    
    if context_info:
        st.json(context_info)
    else:
        st.info("Keine Kontext-Informationen vorhanden.")

# Footer
st.markdown("""
<div class="small-text" style="text-align: center; margin-top: 3rem;">
    <p>API-Monitoring Dashboard v1.0 | Letzte Aktualisierung: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True) 