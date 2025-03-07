#!/usr/bin/env python3

"""
dashboard/app.py

Streamlit-Dashboard zur Überwachung und Visualisierung von AI-API-Nutzung,
Kosten, Cache-Effizienz und Systemmetriken.
"""

import os
import sys
import time
import datetime
import psutil
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta

# Füge das Hauptverzeichnis zum Pfad hinzu, um die Module zu importieren
sys.path.append(str(Path(__file__).parent.parent))
from scripts.ai.cost_tracker import CostTracker
from scripts.ai.prompt_cache import get_cache_stats

# Seitenkonfiguration
st.set_page_config(
    page_title="AI-System Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Seitenstil anpassen
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f0ff;
        border-bottom: 2px solid #4e8cff;
    }
    
    /* Benachrichtigungsstile */
    .notification-container {
        padding: 10px 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
    }
    .notification-icon {
        font-size: 24px;
        margin-right: 10px;
    }
    .notification-content {
        flex-grow: 1;
    }
    .notification-title {
        font-weight: bold;
        margin-bottom: 5px;
    }
    .notification-message {
        font-size: 14px;
    }
    .notification-critical {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
    }
    .notification-warning {
        background-color: #fff8e1;
        border-left: 5px solid #ffc107;
    }
    .notification-info {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
    }
</style>
""", unsafe_allow_html=True)

# Seitentitel
st.title("AI-System Dashboard")
st.markdown("Überwachung von Kosten, Cache-Effizienz und Systemmetriken")

# Initialisiere den CostTracker
cost_tracker = CostTracker()

# Aktualisierungsfunktion
def get_current_time():
    return datetime.now().strftime("%H:%M:%S")

# Funktion zum Sammeln von Systemmetriken über Zeit
@st.cache_data(ttl=300)
def get_historical_metrics(days=7):
    """
    Simuliert historische Systemmetriken für Demonstrationszwecke.
    In einer echten Anwendung würden diese Daten aus einer Datenbank oder Logs gelesen.
    """
    end_date = datetime.now()
    dates = [end_date - timedelta(hours=i) for i in range(24*days, 0, -1)]
    
    # Simulierte Metriken mit realistischen Mustern
    cpu_data = [20 + 15 * np.sin(i/12) + np.random.randint(-5, 10) for i in range(len(dates))]
    memory_data = [40 + 10 * np.sin(i/24) + np.random.randint(-3, 8) for i in range(len(dates))]
    cache_hit_rate = [65 + 15 * np.sin(i/48) + np.random.randint(-5, 5) for i in range(len(dates))]
    
    # Stelle sicher, dass Werte im gültigen Bereich liegen
    cpu_data = [max(0, min(100, x)) for x in cpu_data]
    memory_data = [max(0, min(100, x)) for x in memory_data]
    cache_hit_rate = [max(0, min(100, x)) for x in cache_hit_rate]
    
    df = pd.DataFrame({
        'timestamp': dates,
        'cpu_percent': cpu_data,
        'memory_percent': memory_data,
        'cache_hit_rate': cache_hit_rate
    })
    
    return df

# Funktion zum Generieren von simulierten API-Nutzungsdaten für die Heatmap
@st.cache_data(ttl=300)
def get_api_usage_heatmap_data(days=7):
    """
    Generiert simulierte API-Nutzungsdaten für eine Heatmap-Visualisierung.
    In einer echten Anwendung würden diese Daten aus der Datenbank gelesen.
    """
    end_date = datetime.now()
    
    # Generiere Daten für jeden Tag und jede Stunde
    data = []
    for day in range(days):
        date = end_date - timedelta(days=day)
        for hour in range(24):
            # Simuliere unterschiedliche Nutzungsmuster je nach Tageszeit
            if 9 <= hour <= 17:  # Arbeitsstunden
                usage = np.random.randint(10, 50)  # Höhere Nutzung während der Arbeitszeit
            elif 0 <= hour <= 5:  # Nachtstunden
                usage = np.random.randint(0, 10)   # Niedrigere Nutzung in der Nacht
            else:
                usage = np.random.randint(5, 25)   # Mittlere Nutzung in anderen Zeiten
                
            # Füge Wochentag-Effekt hinzu (weniger Nutzung am Wochenende)
            weekday = date.weekday()
            if weekday >= 5:  # Samstag und Sonntag
                usage = int(usage * 0.5)
                
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'hour': hour,
                'api_calls': usage
            })
    
    return pd.DataFrame(data)

# Sidebar mit Aktualisierungsoptionen
st.sidebar.title("Dashboard-Steuerung")
auto_refresh = st.sidebar.checkbox("Automatische Aktualisierung", value=False)
refresh_interval = st.sidebar.slider("Aktualisierungsintervall (Sekunden)", 
                                    min_value=5, max_value=60, value=30, step=5)

# Zeitraum für Datenvisualisierung
time_period = st.sidebar.selectbox(
    "Zeitraum für Datenvisualisierung",
    ["Letzte 24 Stunden", "Letzte 7 Tage", "Letzter Monat"],
    index=1
)

# Konvertiere Zeitraum in Tage für die Datenabfrage
if time_period == "Letzte 24 Stunden":
    days_to_show = 1
elif time_period == "Letzte 7 Tage":
    days_to_show = 7
else:
    days_to_show = 30

# Lade historische Metriken
historical_metrics = get_historical_metrics(days=days_to_show)

# Hole Kostenzusammenfassung und Cache-Statistiken für Benachrichtigungen
cost_summary = cost_tracker.get_cost_summary()
cache_stats = get_cache_stats()

# Überprüfe und zeige Benachrichtigungen
notifications = check_notifications(cost_summary, cache_stats)

# Zeige Benachrichtigungen im Benachrichtigungsbereich
if notifications:
    st.sidebar.markdown("### Benachrichtigungen")
    for notification in notifications:
        with st.sidebar.expander(notification['title'], expanded=True):
            show_notification(
                notification['title'],
                notification['message'],
                notification['level']
            )

# Aktualisierungslogik
if st.sidebar.button("Jetzt aktualisieren") or auto_refresh:
    st.sidebar.write(f"Letzte Aktualisierung: {get_current_time()}")
    # Leere den Cache, um neue Daten zu laden
    st.cache_data.clear()
    historical_metrics = get_historical_metrics(days=days_to_show)

# Hauptbereich in Tabs aufteilen
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Übersicht", "Kosten-Details", "Cache-Effizienz", "Modell-Nutzung", "System-Metriken"])

with tab1:
    st.header("Dashboard-Übersicht")
    
    # Wichtigste Metriken in Karten anzeigen
    col1, col2, col3, col4 = st.columns(4)
    
    # Aktuelle Systemmetriken
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    # Kostenzusammenfassung
    cost_summary = cost_tracker.get_cost_summary()
    
    # Cache-Statistiken
    cache_stats = get_cache_stats()
    
    with col1:
        st.metric("Heutige Kosten", f"${cost_summary['today_cost']:.2f}", 
                 delta=f"{cost_summary['today_cost'] - cost_summary.get('yesterday_cost', 0):.2f}")
    with col2:
        st.metric("Cache-Trefferrate", f"{cost_summary['cache_hit_rate']:.1%}")
    with col3:
        st.metric("CPU-Auslastung", f"{cpu_percent}%")
    with col4:
        st.metric("Speicherauslastung", f"{memory.percent}%")
    
    # Zeige die wichtigsten Grafiken aus anderen Tabs
    st.subheader("Systemmetriken über Zeit")
    
    # Interaktive Zeitreihen-Grafik mit Plotly
    fig = px.line(historical_metrics, x='timestamp', y=['cpu_percent', 'memory_percent', 'cache_hit_rate'],
                 labels={'timestamp': 'Zeit', 'value': 'Prozent (%)', 'variable': 'Metrik'},
                 title=f"Systemmetriken ({time_period})")
    
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis_title="Prozent (%)",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # NEU: API-Nutzung Heatmap
    st.subheader("API-Nutzung nach Tageszeit")
    
    # Hole Heatmap-Daten
    heatmap_data = get_api_usage_heatmap_data(days=days_to_show)
    
    # Pivot-Tabelle für Heatmap erstellen
    pivot_data = heatmap_data.pivot(index='date', columns='hour', values='api_calls')
    
    # Erstelle Heatmap mit Plotly
    fig_heatmap = px.imshow(
        pivot_data.values,
        labels=dict(x="Stunde des Tages", y="Datum", color="API-Aufrufe"),
        x=list(range(24)),  # Stunden von 0-23
        y=pivot_data.index,
        color_continuous_scale="Viridis",
        title=f"API-Nutzung nach Tageszeit ({time_period})"
    )
    
    fig_heatmap.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(24)),
            ticktext=[f"{h}:00" for h in range(24)]
        ),
        coloraxis_colorbar=dict(
            title="Anzahl der Aufrufe"
        )
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Tägliche Kosten der letzten Woche
    st.subheader("Tägliche Kosten")
    daily_costs = cost_tracker.get_daily_costs(days=days_to_show)
    
    if not daily_costs.empty:
        fig = px.bar(daily_costs, x='date', y='total_cost', 
                    labels={'date': 'Datum', 'total_cost': 'Kosten ($)'},
                    title=f"Tägliche API-Kosten ({time_period})")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Kostendaten verfügbar.")
    
    # Optimierungsempfehlungen
    st.subheader("Optimierungsempfehlungen")
    recommendations = cost_tracker.get_optimization_recommendations()
    
    for rec in recommendations:
        severity = rec['severity']
        message = rec['message']
        
        if severity == "high":
            st.error(message)
        elif severity == "medium":
            st.warning(message)
        else:
            st.info(message)

with tab2:
    st.header("Kosten-Übersicht")
    
    # Kostenzusammenfassung
    cost_summary = cost_tracker.get_cost_summary()
    
    # Metriken in Spalten anzeigen
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Heutige Kosten", f"${cost_summary['today_cost']:.2f}")
    with col2:
        st.metric("Monatskosten", f"${cost_summary['month_cost']:.2f}")
    with col3:
        st.metric("Gesamtkosten", f"${cost_summary['total_cost']:.2f}")
    with col4:
        st.metric("Cache-Trefferrate", f"{cost_summary['cache_hit_rate']:.1%}")
    
    # Budget-Fortschrittsbalken
    st.subheader("Budget-Nutzung")
    daily_budget = cost_summary['daily_budget']
    monthly_budget = cost_summary['monthly_budget']
    
    # Tägliches Budget
    daily_percent = (daily_budget['used'] / daily_budget['limit']) * 100 if daily_budget['limit'] > 0 else 0
    st.write(f"Tägliches Budget: ${daily_budget['used']:.2f} / ${daily_budget['limit']:.2f}")
    st.progress(min(daily_percent / 100, 1.0))
    
    # Monatliches Budget
    monthly_percent = (monthly_budget['used'] / monthly_budget['limit']) * 100 if monthly_budget['limit'] > 0 else 0
    st.write(f"Monatliches Budget: ${monthly_budget['used']:.2f} / ${monthly_budget['limit']:.2f}")
    st.progress(min(monthly_percent / 100, 1.0))
    
    # Tägliche Kosten der letzten Woche
    st.subheader(f"Tägliche Kosten ({time_period})")
    daily_costs = cost_tracker.get_daily_costs(days=days_to_show)
    
    if not daily_costs.empty:
        fig = px.bar(daily_costs, x='date', y='total_cost', 
                    labels={'date': 'Datum', 'total_cost': 'Kosten ($)'},
                    title="Tägliche API-Kosten")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Keine Kostendaten für {time_period} verfügbar.")
    
    # Kostentrend-Analyse
    if not daily_costs.empty and len(daily_costs) > 1:
        st.subheader("Kostentrend-Analyse")
        
        # Berechne gleitenden Durchschnitt
        daily_costs['moving_avg'] = daily_costs['total_cost'].rolling(window=min(7, len(daily_costs)), min_periods=1).mean()
        
        # Trend-Visualisierung
        fig = px.line(daily_costs, x='date', y=['total_cost', 'moving_avg'],
                     labels={'date': 'Datum', 'value': 'Kosten ($)', 'variable': 'Typ'},
                     title="Kostentrend mit gleitendem 7-Tage-Durchschnitt")
        
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Kostenprognose für den nächsten Monat basierend auf aktuellem Trend
        avg_daily_cost = daily_costs['total_cost'].mean()
        projected_monthly = avg_daily_cost * 30
        
        st.info(f"Basierend auf dem aktuellen Trend werden die geschätzten Kosten für den nächsten Monat ${projected_monthly:.2f} betragen.")

with tab3:
    st.header("Cache-Effizienz")
    
    # Cache-Statistiken abrufen
    cache_stats = get_cache_stats()
    
    # Metriken in Spalten anzeigen
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cache-Einträge", cache_stats.get('total_entries', 0))
    with col2:
        st.metric("Cache-Größe", f"{cache_stats.get('total_size_kb', 0):.1f} KB")
    with col3:
        st.metric("Trefferrate", f"{cache_stats.get('metrics', {}).get('hit_rate', 0):.1%}")
    with col4:
        st.metric("Zeit gespart", f"{cache_stats.get('metrics', {}).get('time_saved', 0):.1f} s")
    
    # Cache-Treffer-Verteilung
    st.subheader("Cache-Treffer-Verteilung")
    
    metrics = cache_stats.get('metrics', {})
    exact_hits = metrics.get('exact_hits', 0)
    semantic_hits = metrics.get('semantic_hits', 0)
    misses = metrics.get('misses', 0)
    
    if exact_hits + semantic_hits + misses > 0:
        fig = go.Figure(data=[
            go.Pie(
                labels=['Exakte Treffer', 'Semantische Treffer', 'Fehlschläge'],
                values=[exact_hits, semantic_hits, misses],
                hole=.3,
                marker=dict(colors=['#4CAF50', '#2196F3', '#F44336'])
            )
        ])
        fig.update_layout(title_text="Verteilung der Cache-Zugriffe")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Cache-Daten verfügbar.")
    
    # Cache-Effizienz über Zeit (simulierte Daten)
    st.subheader("Cache-Effizienz über Zeit")
    
    # Verwende die historischen Metriken für die Cache-Trefferrate
    cache_history = historical_metrics[['timestamp', 'cache_hit_rate']].copy()
    cache_history.columns = ['timestamp', 'hit_rate']
    
    fig = px.line(cache_history, x='timestamp', y='hit_rate',
                 labels={'timestamp': 'Zeit', 'hit_rate': 'Trefferrate (%)'},
                 title=f"Cache-Trefferrate über Zeit ({time_period})")
    
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    
    # Cache-Optimierungsvorschläge
    st.subheader("Cache-Optimierungsvorschläge")
    
    # Beispielhafte Vorschläge basierend auf Cache-Statistiken
    if metrics.get('hit_rate', 0) < 0.5:
        st.warning("Die Cache-Trefferrate ist niedrig. Erwägen Sie, den semantischen Schwellenwert anzupassen oder die TTL zu erhöhen.")
    
    if cache_stats.get('total_size_kb', 0) > 10000:
        st.warning("Die Cache-Größe ist hoch. Erwägen Sie eine regelmäßige Bereinigung oder Reduzierung der maximalen Einträge.")
    
    if metrics.get('semantic_hit_rate', 0) < 0.2 and metrics.get('hit_rate', 0) > 0.5:
        st.info("Die semantische Trefferrate ist niedrig. Überprüfen Sie den Ähnlichkeitsschwellenwert oder die Embedding-Qualität.")

with tab4:
    st.header("Modell-Nutzung")
    
    # NEU: Filter für Modelle
    st.sidebar.markdown("### Modell-Filter")
    
    # Modellkosten abrufen
    model_costs = cost_tracker.get_model_costs(days=days_to_show)
    
    if not model_costs.empty:
        # Liste aller verfügbaren Modelle
        available_models = model_costs['model_id'].unique().tolist()
        
        # Multiselect für Modellfilter
        selected_models = st.sidebar.multiselect(
            "Modelle auswählen",
            options=available_models,
            default=available_models
        )
        
        # Filtere Daten basierend auf Auswahl
        if selected_models:
            filtered_model_costs = model_costs[model_costs['model_id'].isin(selected_models)]
        else:
            filtered_model_costs = model_costs
            st.warning("Keine Modelle ausgewählt. Zeige alle Daten.")
        
        # Modellkosten-Tabelle
        st.subheader(f"Modellkosten ({time_period})")
        
        # Sortieroptionen
        sort_column = st.selectbox(
            "Sortieren nach",
            options=["model_id", "total_cost", "call_count", "avg_cost_per_call", "cost_per_1k_tokens"],
            index=1  # Standardmäßig nach Gesamtkosten sortieren
        )
        
        sort_order = st.radio(
            "Sortierreihenfolge",
            options=["Absteigend", "Aufsteigend"],
            horizontal=True
        )
        
        # Sortiere Daten
        ascending = sort_order == "Aufsteigend"
        filtered_model_costs = filtered_model_costs.sort_values(by=sort_column, ascending=ascending)
        
        # Formatiere die Tabelle
        display_df = filtered_model_costs.copy()
        display_df['total_cost'] = display_df['total_cost'].map('${:.2f}'.format)
        display_df['avg_cost_per_call'] = display_df['avg_cost_per_call'].map('${:.4f}'.format)
        display_df['cost_per_1k_tokens'] = display_df['cost_per_1k_tokens'].map('${:.4f}'.format)
        
        st.dataframe(display_df[['model_id', 'total_cost', 'call_count', 
                               'avg_cost_per_call', 'cost_per_1k_tokens']])
        
        # Modellkosten-Diagramm
        st.subheader("Kostenverteilung nach Modell")
        fig = px.pie(filtered_model_costs, values='total_cost', names='model_id',
                    title="Anteil der Gesamtkosten nach Modell")
        st.plotly_chart(fig, use_container_width=True)
        
        # Modellnutzung-Diagramm
        st.subheader("Nutzung nach Modell")
        fig = px.bar(filtered_model_costs, x='model_id', y='call_count',
                    title="Anzahl der API-Aufrufe nach Modell")
        st.plotly_chart(fig, use_container_width=True)
        
        # Kosten-Effizienz-Analyse
        st.subheader("Kosten-Effizienz-Analyse")
        
        # Berechne Kosten pro Token für jedes Modell
        efficiency_df = filtered_model_costs.copy()
        efficiency_df['cost_per_token'] = efficiency_df['total_cost'] / (efficiency_df['input_tokens'] + efficiency_df['output_tokens'])
        efficiency_df = efficiency_df.sort_values('cost_per_token')
        
        fig = px.bar(efficiency_df, x='model_id', y='cost_per_token',
                    labels={'model_id': 'Modell', 'cost_per_token': 'Kosten pro Token ($)'},
                    title="Kosten-Effizienz nach Modell (niedrigere Werte sind besser)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Modellnutzungsdaten verfügbar.")

with tab5:
    st.header("System-Metriken")
    
    # System-Metriken in Spalten anzeigen
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cpu_percent = psutil.cpu_percent()
        st.metric("CPU-Auslastung", f"{cpu_percent}%")
    
    with col2:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        st.metric("Speicherauslastung", f"{memory_percent}%")
    
    with col3:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        st.metric("Festplattennutzung", f"{disk_percent}%")
    
    with col4:
        # Anzahl der Python-Prozesse
        python_count = len([p for p in psutil.process_iter(['name']) 
                          if 'python' in p.info['name'].lower()])
        st.metric("Python-Prozesse", python_count)
    
    # CPU-Auslastung-Diagramm über Zeit
    st.subheader("CPU-Auslastung über Zeit")
    
    # Verwende die historischen Metriken
    cpu_history = historical_metrics[['timestamp', 'cpu_percent']].copy()
    
    fig = px.line(cpu_history, x='timestamp', y='cpu_percent',
                 labels={'timestamp': 'Zeit', 'cpu_percent': 'CPU (%)'},
                 title=f"CPU-Auslastung ({time_period})")
    
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    
    # Speicherauslastung-Diagramm über Zeit
    st.subheader("Speicherauslastung über Zeit")
    
    # Verwende die historischen Metriken
    memory_history = historical_metrics[['timestamp', 'memory_percent']].copy()
    
    fig = px.line(memory_history, x='timestamp', y='memory_percent',
                 labels={'timestamp': 'Zeit', 'memory_percent': 'Speicher (%)'},
                 title=f"Speicherauslastung ({time_period})")
    
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    
    # Speicherdetails
    st.subheader("Aktuelle Speichernutzung")
    memory = psutil.virtual_memory()
    memory_data = {
        'Kategorie': ['Verwendet', 'Verfügbar'],
        'Größe (GB)': [memory.used / (1024**3), memory.available / (1024**3)]
    }
    memory_df = pd.DataFrame(memory_data)
    
    fig = px.bar(memory_df, x='Kategorie', y='Größe (GB)',
                title="Speichernutzung (GB)")
    st.plotly_chart(fig, use_container_width=True)
    
    # Systemressourcen-Überwachung
    st.subheader("Detaillierte Systemressourcen")
    
    # Erweiterte Systemmetriken in Expander
    with st.expander("Erweiterte CPU-Informationen"):
        # CPU-Informationen
        cpu_times = psutil.cpu_times_percent()
        cpu_data = {
            'Metrik': ['Benutzer', 'System', 'Leerlauf', 'Interrupt'],
            'Prozent': [cpu_times.user, cpu_times.system, cpu_times.idle, cpu_times.interrupt]
        }
        cpu_df = pd.DataFrame(cpu_data)
        
        fig = px.bar(cpu_df, x='Metrik', y='Prozent',
                    title="CPU-Zeitverteilung")
        st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Netzwerkstatistiken"):
        # Netzwerkstatistiken
        net_io = psutil.net_io_counters()
        st.write(f"Bytes gesendet: {net_io.bytes_sent / (1024**2):.2f} MB")
        st.write(f"Bytes empfangen: {net_io.bytes_recv / (1024**2):.2f} MB")
        st.write(f"Pakete gesendet: {net_io.packets_sent}")
        st.write(f"Pakete empfangen: {net_io.packets_recv}")

# Footer
st.markdown("---")
st.markdown("**AI-System Dashboard** | Entwickelt für die Überwachung von AI-API-Nutzung und Systemmetriken")

# Automatische Aktualisierung
if auto_refresh:
    time.sleep(refresh_interval)
    st.experimental_rerun()

# Funktion zur Anzeige von Benachrichtigungen
def show_notification(title, message, level="info"):
    """
    Zeigt eine formatierte Benachrichtigung an.
    
    Args:
        title (str): Titel der Benachrichtigung
        message (str): Nachrichtentext
        level (str): Schweregrad (info, warning, critical)
    """
    icon = {
        "info": "ℹ️",
        "warning": "⚠️",
        "critical": "🚨"
    }.get(level, "ℹ️")
    
    notification_class = f"notification-{level}"
    
    html = f"""
    <div class="notification-container {notification_class}">
        <div class="notification-icon">{icon}</div>
        <div class="notification-content">
            <div class="notification-title">{title}</div>
            <div class="notification-message">{message}</div>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)

# Funktion zur Überprüfung von Benachrichtigungsbedingungen
def check_notifications(cost_summary, cache_stats):
    """
    Überprüft Bedingungen für Benachrichtigungen und zeigt sie an.
    
    Args:
        cost_summary (dict): Kostenzusammenfassung vom CostTracker
        cache_stats (dict): Cache-Statistiken
    
    Returns:
        list: Liste der angezeigten Benachrichtigungen
    """
    notifications = []
    
    # Budget-Warnungen
    daily_budget = cost_summary.get('daily_budget', {})
    monthly_budget = cost_summary.get('monthly_budget', {})
    
    daily_limit = daily_budget.get('limit', 0)
    daily_used = daily_budget.get('used', 0)
    
    monthly_limit = monthly_budget.get('limit', 0)
    monthly_used = monthly_budget.get('used', 0)
    
    # Tägliches Budget
    if daily_limit > 0:
        daily_percent = (daily_used / daily_limit) * 100
        if daily_percent >= 90:
            notifications.append({
                'title': 'Kritische Budget-Warnung',
                'message': f'Tägliches Budget zu {daily_percent:.1f}% aufgebraucht (${daily_used:.2f} von ${daily_limit:.2f}).',
                'level': 'critical'
            })
        elif daily_percent >= 75:
            notifications.append({
                'title': 'Budget-Warnung',
                'message': f'Tägliches Budget zu {daily_percent:.1f}% aufgebraucht (${daily_used:.2f} von ${daily_limit:.2f}).',
                'level': 'warning'
            })
    
    # Monatliches Budget
    if monthly_limit > 0:
        monthly_percent = (monthly_used / monthly_limit) * 100
        if monthly_percent >= 90:
            notifications.append({
                'title': 'Kritische Budget-Warnung',
                'message': f'Monatliches Budget zu {monthly_percent:.1f}% aufgebraucht (${monthly_used:.2f} von ${monthly_limit:.2f}).',
                'level': 'critical'
            })
        elif monthly_percent >= 75:
            notifications.append({
                'title': 'Budget-Warnung',
                'message': f'Monatliches Budget zu {monthly_percent:.1f}% aufgebraucht (${monthly_used:.2f} von ${monthly_limit:.2f}).',
                'level': 'warning'
            })
    
    # Cache-Trefferquote
    metrics = cache_stats.get('metrics', {})
    hit_rate = metrics.get('hit_rate', 0)
    
    if hit_rate < 0.3:
        notifications.append({
            'title': 'Niedrige Cache-Trefferquote',
            'message': f'Die Cache-Trefferquote ist sehr niedrig ({hit_rate:.1%}). Überprüfen Sie die Cache-Einstellungen.',
            'level': 'warning'
        })
    
    # Cache-Größe
    total_size_kb = cache_stats.get('total_size_kb', 0)
    if total_size_kb > 10000:  # Größer als 10 MB
        notifications.append({
            'title': 'Große Cache-Größe',
            'message': f'Der Cache ist sehr groß ({total_size_kb/1024:.1f} MB). Erwägen Sie eine Cache-Bereinigung.',
            'level': 'info'
        })
    
    return notifications 