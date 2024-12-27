{pkgs}: {
  deps = [
    pkgs.chromium
    pkgs.libgcc
    pkgs.pango
    pkgs.cairo
    pkgs.freetype
    pkgs.fontconfig
    pkgs.nss
    pkgs.glib
    pkgs.postgresql
  ];
}
