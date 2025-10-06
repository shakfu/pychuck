from textual.widgets import DataTable
from textual.reactive import reactive

class ShredList(DataTable):
    """Widget to display running shreds"""

    def on_mount(self) -> None:
        self.add_columns("ID", "Name", "Status")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def refresh_shreds(self, chuck, session):
        """Update shred list"""
        self.clear()

        try:
            all_shreds = chuck.get_all_shred_ids()
            ready_shreds = set(chuck.get_ready_shred_ids())
            blocked_shreds = set(chuck.get_blocked_shred_ids())

            for shred_id in all_shreds:
                name = session.get_shred_name(shred_id)

                # Determine status
                if shred_id in ready_shreds:
                    status = "[green]ready[/green]"
                elif shred_id in blocked_shreds:
                    status = "[yellow]blocked[/yellow]"
                else:
                    status = "[dim]unknown[/dim]"

                self.add_row(
                    f"[cyan]{shred_id}[/cyan]",
                    name[:35] + "..." if len(name) > 35 else name,
                    status,
                    key=str(shred_id)
                )
        except Exception as e:
            self.add_row("[red]Error[/red]", str(e), "")

    async def on_data_table_row_selected(self, event) -> None:
        """Handle row selection - could show shred details"""
        pass
