from textual.widgets import DataTable

class GlobalsPanel(DataTable):
    """Widget to display global variables"""

    def on_mount(self) -> None:
        self.add_columns("Name", "Type")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def refresh_globals(self, chuck):
        """Update globals list"""
        self.clear()

        try:
            globals_list = chuck.get_all_globals()

            for typ, name in globals_list[:20]:  # Limit to first 20
                # Truncate long type names
                type_str = typ if len(typ) <= 15 else typ[:12] + "..."

                self.add_row(
                    f"[yellow]{name}[/yellow]",
                    f"[dim]{type_str}[/dim]",
                    key=name
                )

            if len(globals_list) > 20:
                self.add_row(
                    f"[dim]...and {len(globals_list) - 20} more[/dim]",
                    ""
                )
        except Exception as e:
            self.add_row(f"[red]Error: {e}[/red]", "")
