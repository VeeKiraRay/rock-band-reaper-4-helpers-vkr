# Optional standalone launchers

These launchers are retained for isolated testing and advanced troubleshooting.
They are not normal release entry points. Register
`rock_band_general_helper_vkr.py` from the repository root and open additional
windows from inside the General Helper.

Do not run a standalone launcher beside the General Helper or another
persistent Python ReaScript. REAPER's embedded Python runtime can invalidate
the action that was opened first and may crash REAPER.
