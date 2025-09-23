"""
TouchDesigner Project Manager Extension
Manages project state, settings, and data flow coordination.
"""

try:
    from td import COMP, DAT, OP, Par
except ImportError:
    OP = COMP = DAT = Par = "OP"  # Fallback for development


class ProjectManager:
    """Main project manager for coordinating all project components."""

    def __init__(self, ownerComp: COMP) -> None:
        self.ownerComp: COMP = ownerComp
        self.IsInitialized = False
        self.ProjectName = ""
        self.DebugMode = False
        self._initialize_references()

    def _initialize_references(self) -> None:
        """Initialize all internal references to TouchDesigner components."""
        try:
            self._config_dat = self.ownerComp.op("Config_Data")
            self._log_dat = self.ownerComp.op("Project_Log")
            self._state_dat = self.ownerComp.op("State_Manager")

            if not self._config_dat:
                raise LookupError("'Config_Data' DAT not found in ownerComp")

        except AttributeError as e:
            raise AttributeError(f"Invalid ownerComp reference: {e}")

    def initialize_project(self, project_name: str = None) -> bool:
        """
        Initialize the project with specified name and settings.

        Args:
            project_name: Name for the project, defaults to file name

        Returns:
            True if initialization successful
        """
        try:
            if project_name:
                self.ProjectName = project_name
            else:
                self.ProjectName = project.name if project else "Untitled_Project"

            # Initialize project settings
            self._setup_default_parameters()
            self._configure_logging()
            self._initialize_data_flow()

            self.IsInitialized = True
            self._log_message(f"Project '{self.ProjectName}' initialized successfully")

            return True

        except Exception as e:
            self._log_error(f"Project initialization failed: {e}")
            return False

    def _setup_default_parameters(self) -> None:
        """Set up default project parameters and custom parameters."""
        try:
            # Create custom parameters if they don't exist
            if not hasattr(self.ownerComp.par, "Projectname"):
                self.ownerComp.appendPar("Projectname", val=self.ProjectName)

            if not hasattr(self.ownerComp.par, "Debugmode"):
                self.ownerComp.appendPar("Debugmode", val=False)

            # Update parameter values
            self.ownerComp.par.Projectname.val = self.ProjectName
            self.DebugMode = self.ownerComp.par.Debugmode.val

        except Exception as e:
            raise ValueError(f"Parameter setup failed: {e}")

    def _configure_logging(self) -> None:
        """Configure project logging system."""
        if self._log_dat:
            self._log_dat.clear()
            self._log_dat.appendRow(["Timestamp", "Level", "Message"])

    def _initialize_data_flow(self) -> None:
        """Initialize data flow connections and processing chain."""
        try:
            # Set up data processing pipeline
            input_ops = self.ownerComp.findChildren(type=CHOP, name="*_input")
            for input_op in input_ops:
                self._configure_input_operator(input_op)

        except Exception as e:
            self._log_error(f"Data flow initialization error: {e}")

    def _configure_input_operator(self, input_op: OP) -> None:
        """Configure individual input operator for data processing."""
        if hasattr(input_op.par, "active"):
            input_op.par.active = True

    def onValueChange(self, par: Par, prev: float) -> None:
        """
        Callback for parameter value changes.
        Handles project settings updates and state management.
        """
        try:
            if par.name == "Debugmode":
                self.DebugMode = bool(par.val)
                self._log_message(
                    f"Debug mode {'enabled' if self.DebugMode else 'disabled'}"
                )

            elif par.name == "Projectname":
                self.ProjectName = par.val
                self._log_message(f"Project name changed to: {self.ProjectName}")

        except Exception as e:
            self._log_error(f"Parameter change error: {e}")

    def onPulse(self, par: Par) -> None:
        """Handle button pulse events for project actions."""
        try:
            if par.name == "Resetproject":
                self.reset_project()
            elif par.name == "Savestate":
                self.save_project_state()
            elif par.name == "Loadstate":
                self.load_project_state()

        except Exception as e:
            self._log_error(f"Pulse action error: {e}")

    def reset_project(self) -> None:
        """Reset project to initial state."""
        try:
            self.IsInitialized = False
            self._configure_logging()
            self.initialize_project(self.ProjectName)
            self._log_message("Project reset completed")

        except Exception as e:
            self._log_error(f"Project reset failed: {e}")

    def save_project_state(self) -> None:
        """Save current project state to storage."""
        try:
            state_data = {
                "project_name": self.ProjectName,
                "debug_mode": self.DebugMode,
                "initialized": self.IsInitialized,
                "timestamp": absTime.frame,
            }

            if self._state_dat:
                self._state_dat.text = str(state_data)

            self._log_message("Project state saved")

        except Exception as e:
            self._log_error(f"State save failed: {e}")

    def load_project_state(self) -> None:
        """Load project state from storage."""
        try:
            if self._state_dat and self._state_dat.text:
                state_data = eval(self._state_dat.text)

                self.ProjectName = state_data.get("project_name", self.ProjectName)
                self.DebugMode = state_data.get("debug_mode", False)
                self.IsInitialized = state_data.get("initialized", False)

                self._update_parameters()
                self._log_message("Project state loaded")
            else:
                self._log_message("No saved state found")

        except Exception as e:
            self._log_error(f"State load failed: {e}")

    def _update_parameters(self) -> None:
        """Update component parameters to match loaded state."""
        if hasattr(self.ownerComp.par, "Projectname"):
            self.ownerComp.par.Projectname.val = self.ProjectName
        if hasattr(self.ownerComp.par, "Debugmode"):
            self.ownerComp.par.Debugmode.val = self.DebugMode

    def _log_message(self, message: str) -> None:
        """Log informational message."""
        if self._log_dat:
            timestamp = absTime.seconds
            self._log_dat.appendRow([timestamp, "INFO", message])

        if self.DebugMode:
            print(f"ProjectManager: {message}")

    def _log_error(self, message: str) -> None:
        """Log error message."""
        if self._log_dat:
            timestamp = absTime.seconds
            self._log_dat.appendRow([timestamp, "ERROR", message])

        print(f"ProjectManager ERROR: {message}")

    def get_project_info(self) -> dict:
        """
        Get comprehensive project information.

        Returns:
            Dictionary with project status and configuration
        """
        return {
            "name": self.ProjectName,
            "initialized": self.IsInitialized,
            "debug_mode": self.DebugMode,
            "components": {
                "config_dat": self._config_dat is not None,
                "log_dat": self._log_dat is not None,
                "state_dat": self._state_dat is not None,
            },
        }
