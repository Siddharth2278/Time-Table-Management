"""Import preview dialog: review/correct extracted rows before training.

Shows one row per extracted lecture with an Approve checkbox. The user can
edit cells inline, delete wrong rows, add missing rows and approve only
what is correct. Only approved rows ever reach the training dataset.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from app.services.timetable_import.models import TimetableRecord
from app.ui.base_dialog import BaseDialog
from app.ui.modals import error as modal_error

COLUMNS = ["Approve", "Day", "Start", "End", "Subject", "Teacher", "Room",
           "Confidence", "Warnings"]


class ImportPreviewDialog(BaseDialog):
    """Editable timetable-style preview of extracted records."""

    def __init__(self, parent, extractions, reports, errors):
        super().__init__(parent, "Review Extracted Data", min_width=860)
        self.setMinimumHeight(520)
        self._records = []
        for extraction in extractions:
            self._records.extend(extraction.records)
        summary = QLabel("\n".join(
            f"{r['file']}: {r['lectures']} lectures "
            f"(high {r['high']}, medium {r['medium']}, low {r['low']})"
            + (f" — {'; '.join(r['warnings'][:2])}" if r["warnings"] else "")
            for r in reports) or "No files analyzed.")
        summary.setObjectName("InfoBar")
        summary.setWordWrap(True)
        self.body_layout.addWidget(summary)
        if errors:
            err_label = QLabel("\n".join(
                f"{e['file']}: {e['error']}" for e in errors))
            err_label.setObjectName("Muted")
            err_label.setWordWrap(True)
            self.body_layout.addWidget(err_label)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(260)
        self.body_layout.addWidget(self.table)

        row_btns = QHBoxLayout()
        self.add_btn = QPushButton("Add Row")
        self.add_btn.setObjectName("SecondaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_row)
        row_btns.addWidget(self.add_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("SecondaryButton")
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.clicked.connect(self._delete_selected)
        row_btns.addWidget(self.del_btn)
        row_btns.addStretch()
        self.body_layout.addLayout(row_btns)
        self._fill()

    def _fill(self):
        self.table.setRowCount(len(self._records))
        for row_idx, record in enumerate(self._records):
            approve = QTableWidgetItem()
            approve.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            approve.setCheckState(Qt.Checked if record.confidence >= 0.5
                                  else Qt.Unchecked)
            self.table.setItem(row_idx, 0, approve)
            values = [record.day, record.start, record.end, record.subject,
                      record.teacher, record.room,
                      f"{record.confidence:.2f}",
                      "; ".join(record.warnings[:2])]
            for col_idx, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                if col_idx < 7:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

    def _add_row(self):
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        approve = QTableWidgetItem()
        approve.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        approve.setCheckState(Qt.Checked)
        self.table.setItem(row_idx, 0, approve)
        for col_idx in range(1, 7):
            item = QTableWidgetItem("")
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.table.setItem(row_idx, col_idx, item)
        self.table.setItem(row_idx, 7, QTableWidgetItem("1.00"))
        self.table.setItem(row_idx, 8, QTableWidgetItem("manual"))

    def _delete_selected(self):
        rows = sorted({item.row() for item in self.table.selectedItems()},
                      reverse=True)
        for row_idx in rows:
            self.table.removeRow(row_idx)

    def approved_records(self):
        """Records with Approve checked, reflecting inline edits."""
        out = []
        for row_idx in range(self.table.rowCount()):
            approve = self.table.item(row_idx, 0)
            if approve is None or approve.checkState() != Qt.Checked:
                continue
            cells = [(self.table.item(row_idx, c).text()
                      if self.table.item(row_idx, c) else "")
                     for c in range(1, 9)]
            day, start, end, subject, teacher, room, conf, _warn = cells
            try:
                confidence = float(conf or 0)
            except (TypeError, ValueError):
                confidence = 0.5
            base = self._records[row_idx] if row_idx < len(self._records) else None
            out.append(TimetableRecord(
                day=day.strip(), start=start.strip(), end=end.strip(),
                subject=subject.strip(), teacher=teacher.strip(),
                room=room.strip(),
                semester=base.semester if base else "",
                lecture_type=base.lecture_type if base else "Theory",
                is_lab=base.is_lab if base else False,
                source_file=base.source_file if base else "manual",
                source_page=base.source_page if base else 0,
                confidence=max(0.0, min(1.0, confidence))))
        return out

    def accept(self):
        if not self.approved_records():
            modal_error(self, "Nothing Approved",
                        "Approve at least one row before training.")
            return
        super().accept()


def open_import_preview(parent, extractions, reports, errors):
    dialog = ImportPreviewDialog(parent, extractions, reports, errors)
    if dialog.exec():
        return dialog.approved_records()
    return None
