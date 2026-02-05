from app.ui.library_menu import LibraryMenu


class CurrentlyWatchingMenu(LibraryMenu):
    def __init__(self, back_callback, parent=None):
        super().__init__(
            back_callback=back_callback,
            parent=parent,
            show_only_watching=True,
            title_text="Watching",
        )
