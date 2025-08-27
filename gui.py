import tkinter as tk
from tkinter import ttk

class HoursEstimatorApp(tk.Tk):
    """Simple GUI to estimate total hours for tasks."""
    def __init__(self):
        super().__init__()
        self.title("Hours Estimator")
        self.geometry("300x200")
        self._build_widgets()

    def _build_widgets(self):
        # Number of tasks input
        task_label = ttk.Label(self, text="Number of tasks:")
        task_label.pack(pady=(10, 0))
        self.task_entry = ttk.Entry(self)
        self.task_entry.pack()

        # Average hours per task input
        hours_label = ttk.Label(self, text="Average hours per task:")
        hours_label.pack(pady=(10, 0))
        self.hours_entry = ttk.Entry(self)
        self.hours_entry.pack()

        # Result display
        self.result_label = ttk.Label(self, text="")
        self.result_label.pack(pady=10)

        # Calculate button
        calc_button = ttk.Button(self, text="Estimate", command=self._calculate)
        calc_button.pack()

    def _calculate(self):
        """Calculate total estimated hours."""
        try:
            tasks = int(self.task_entry.get())
            hours_per = float(self.hours_entry.get())
            total = tasks * hours_per
            self.result_label.config(text=f"Estimated hours: {total:.2f}")
        except ValueError:
            self.result_label.config(text="Invalid input")


if __name__ == "__main__":
    app = HoursEstimatorApp()
    app.mainloop()
