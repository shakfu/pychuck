from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.formatted_text import HTML

class TabbedApp:
    def __init__(self):
        self.current_tab = 0
        self.tabs = [
            {"name": "1", "content": self.create_home_tab()},
            {"name": "2", "content": self.create_editor_tab()},
            {"name": "3", "content": self.create_info_tab()},
        ]
        
        # Key bindings
        self.kb = KeyBindings()
        self.setup_key_bindings()
        
        # Create layout
        self.layout = Layout(self.create_layout())
        
        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )
    
    def setup_key_bindings(self):
        @self.kb.add('c-c')
        @self.kb.add('c-q')
        def exit_app(event):
            event.app.exit()
        
        @self.kb.add('right')
        @self.kb.add('tab')
        def next_tab(event):
            self.current_tab = (self.current_tab + 1) % len(self.tabs)
            self.layout.container = self.create_layout()
        
        @self.kb.add('left')
        @self.kb.add('s-tab')
        def prev_tab(event):
            self.current_tab = (self.current_tab - 1) % len(self.tabs)
            self.layout.container = self.create_layout()
    
    def create_tab_bar(self):
        """Create the tab bar with clickable tabs"""
        tab_buttons = []
        for i, tab in enumerate(self.tabs):
            if i == self.current_tab:
                tab_text = f" [{tab['name']}] "
            else:
                tab_text = f"  {tab['name']}  "
            tab_buttons.append(tab_text)
        
        tab_bar_text = "".join(tab_buttons)
        return Window(
            content=FormattedTextControl(text=tab_bar_text),
            height=1,
            style='bg:#3366cc fg:#ffffff'
        )
    
    def create_home_tab(self):
        """Create content for Home tab"""
        text = """
        Welcome to the Tabbed Application!
        
        Navigation:
        - Tab / Right Arrow: Next tab
        - Shift+Tab / Left Arrow: Previous tab
        - Ctrl+C or Ctrl+Q: Exit
        
        This is a demo of a full-screen tabbed interface
        built with prompt-toolkit.
        """
        return Window(
            content=FormattedTextControl(text=text),
            wrap_lines=True
        )
    
    def create_editor_tab(self):
        """Create content for Editor tab"""
        self.text_area = TextArea(
            text="Type something here...\n\nThis is an editable text area.",
            multiline=True,
            scrollbar=True
        )
        return self.text_area
    
    def create_info_tab(self):
        """Create content for Info tab"""
        text = """
        Information Tab
        
        Current Application Details:
        - Framework: prompt-toolkit
        - Type: Full-screen terminal UI
        - Features: Multiple tabs, keyboard navigation
        
        You can add any content here:
        - Forms
        - Lists
        - Tables
        - Custom widgets
        """
        return Window(
            content=FormattedTextControl(text=text),
            wrap_lines=True
        )
    
    def create_layout(self):
        """Create the main layout with tab bar and content"""
        return HSplit([
            self.create_tab_bar(),
            Frame(
                body=self.tabs[self.current_tab]["content"],
                title=self.tabs[self.current_tab]["name"]
            ),
            Window(
                content=FormattedTextControl(
                    text=" Ctrl+C: Exit | Tab/Shift+Tab: Switch tabs "
                ),
                height=1,
                style='bg:#444444 fg:#ffffff'
            )
        ])
    
    def run(self):
        """Run the application"""
        self.app.run()

if __name__ == "__main__":
    app = TabbedApp()
    app.run()
