from __future__ import annotations

import sys
from typing import Dict

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QFormLayout,
    QSpinBox,
    QLineEdit,
    QCheckBox,
    QLabel,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt

from models import DEFAULT_KIT_DEFS, PARAM_DEFS, MARKET_PROFILES, KitInstance
from estimate import Estimate


class KitEditor(QWidget):
    def __init__(self, kit: KitInstance):
        super().__init__()
        self.kit = kit
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()
        self.fields: Dict[str, QWidget] = {}
        self.name_edit = QLineEdit()
        layout.addRow("name", self.name_edit)
        params = PARAM_DEFS.get(self.kit.definition.code, {})
        for name, typ in params.items():
            if typ is bool:
                widget = QCheckBox()
            elif typ is float:
                widget = QLineEdit()
            else:
                widget = QSpinBox()
                widget.setMaximum(1_000_000)
            layout.addRow(name, widget)
            self.fields[name] = widget
        self.deliverables = QSpinBox()
        self.deliverables.setMaximum(1_000_000)
        layout.addRow("deliverables", self.deliverables)
        self.setLayout(layout)
        self.load_from_kit()

    def load_from_kit(self):
        self.name_edit.setText(self.kit.custom_name or "")
        for name, widget in self.fields.items():
            val = self.kit.param_values.get(name, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))
            else:
                widget.setValue(int(val))
        self.deliverables.setValue(self.kit.deliverables)

    def save_to_kit(self):
        for name, widget in self.fields.items():
            if isinstance(widget, QCheckBox):
                self.kit.param_values[name] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                try:
                    self.kit.param_values[name] = float(widget.text())
                except ValueError:
                    self.kit.param_values[name] = 0.0
            else:
                self.kit.param_values[name] = widget.value()
        self.kit.deliverables = self.deliverables.value()
        self.kit.custom_name = self.name_edit.text().strip() or None


class ElementWidget(QWidget):
    def __init__(self, estimate: Estimate, code: str):
        super().__init__()
        self.estimate = estimate
        self.code = code
        self.element = estimate.elements[code]
        self.current_editor: KitEditor | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._kit_selected)
        layout.addWidget(self.list, 1)
        right = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.kit_type_combo = QComboBox()
        for code, defn in DEFAULT_KIT_DEFS.get(self.code, {}).items():
            self.kit_type_combo.addItem(f"{code} {defn.default_name}", defn)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_kit)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_kit)
        dup_btn = QPushButton("Duplicate")
        dup_btn.clicked.connect(self._duplicate_kit)
        btn_layout.addWidget(self.kit_type_combo)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(dup_btn)
        right.addLayout(btn_layout)
        self.editor_container = QVBoxLayout()
        right.addLayout(self.editor_container, 1)
        layout.addLayout(right, 2)
        self.setLayout(layout)
        self.refresh_list()

    def refresh_list(self):
        self.element.compact_indices()
        self.list.clear()
        for kit in self.element.kits:
            self.list.addItem(kit.display_name)

    def _kit_selected(self, row: int):
        for i in reversed(range(self.editor_container.count())):
            item = self.editor_container.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()
        if row < 0 or row >= len(self.element.kits):
            self.current_editor = None
            return
        kit = self.element.kits[row]
        editor = KitEditor(kit)
        self.editor_container.addWidget(editor)
        self.current_editor = editor

    def _add_kit(self):
        defn = self.kit_type_combo.currentData()
        if defn is None:
            return
        index = len([k for k in self.element.kits if k.definition.code == defn.code]) + 1
        kit = KitInstance(defn, index)
        self.element.kits.append(kit)
        self.refresh_list()
        self.list.setCurrentRow(len(self.element.kits) - 1)

    def _remove_kit(self):
        row = self.list.currentRow()
        if row >= 0:
            self.element.kits.pop(row)
            self.refresh_list()
            self._kit_selected(self.list.currentRow())

    def _duplicate_kit(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.element.kits):
            return
        source = self.element.kits[row]
        new_kit = KitInstance(source.definition, 0, source.custom_name)
        new_kit.param_values = source.param_values.copy()
        new_kit.deliverables = source.deliverables
        self.element.kits.append(new_kit)
        self.refresh_list()
        self.list.setCurrentRow(len(self.element.kits) - 1)

    def save_changes(self):
        if self.current_editor:
            self.current_editor.save_to_kit()
            self.refresh_list()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controls Engineering Estimator")
        self.estimate = Estimate()
        self._build_ui()

    def _build_ui(self):
        tabs = QTabWidget()
        self.setup_tab = QWidget()
        self.user_tab = QWidget()
        self.output_tab = QWidget()
        tabs.addTab(self.setup_tab, "Setup")
        tabs.addTab(self.user_tab, "User Input")
        tabs.addTab(self.output_tab, "Estimate Output")
        self.setCentralWidget(tabs)
        self._build_setup_tab()
        self._build_user_tab()
        self._build_output_tab()

    def _build_setup_tab(self):
        layout = QFormLayout()
        self.market_combo = QComboBox()
        for name in MARKET_PROFILES:
            self.market_combo.addItem(name)
        layout.addRow("Market", self.market_combo)
        self.setup_tab.setLayout(layout)

    def _build_user_tab(self):
        layout = QVBoxLayout()
        self.element_tabs = QTabWidget()
        for code in ["51", "52", "53", "54", "60", "70"]:
            widget = ElementWidget(self.estimate, code)
            self.element_tabs.addTab(widget, code)
        layout.addWidget(self.element_tabs)
        save_btn = QPushButton("Save Estimate")
        save_btn.clicked.connect(self.save_estimate)
        layout.addWidget(save_btn)
        self.user_tab.setLayout(layout)

    def _build_output_tab(self):
        layout = QVBoxLayout()
        self.output_label = QLabel("Totals will appear here")
        layout.addWidget(self.output_label)
        calc_btn = QPushButton("Calculate Totals")
        calc_btn.clicked.connect(self.update_totals)
        layout.addWidget(calc_btn)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        layout.addWidget(export_btn)
        self.output_tab.setLayout(layout)

    def update_totals(self):
        current_widget = self.element_tabs.currentWidget()
        if isinstance(current_widget, ElementWidget):
            current_widget.save_changes()
        totals = self.estimate.rollup_totals()
        self.output_label.setText(
            f"Dev: {totals['Dev']:.2f}\nDoc: {totals['Doc']:.2f}\nConfig: {totals['Config']:.2f}"
        )

    def save_estimate(self):
        current_widget = self.element_tabs.currentWidget()
        if isinstance(current_widget, ElementWidget):
            current_widget.save_changes()
        path, _ = QFileDialog.getSaveFileName(self, "Save Estimate", filter="Estimate (*.estimate.json)")
        if not path:
            return
        with open(path, "w") as f:
            f.write(self.estimate.to_json())

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", filter="CSV Files (*.csv)")
        if not path:
            return
        try:
            self.estimate.export_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(900, 600)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
