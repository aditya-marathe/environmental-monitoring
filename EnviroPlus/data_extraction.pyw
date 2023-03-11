#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnviroPlus Data Extraction Tool
-------------------------------
[Description]

Author: A. Marathe
Last Updated: 11-03-2023
"""

import os
import csv
import sqlite3

# UI imports
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

# Typing
from typing import Dict
from typing import List
from typing import Any


def get_bytes_string(file_size: int) -> str:
    """

    :param file_size:
    :return:
    """
    # StackOverflow: @whereisalext and @alper

    bytes_ = float(file_size)
    k_bytes = float(1024)
    m_bytes = float(k_bytes ** 2)
    g_bytes = float(k_bytes ** 3)
    t_bytes = float(k_bytes ** 4)

    if bytes_ < k_bytes:
        return '{0} B'.format(bytes_)
    elif k_bytes <= bytes_ < m_bytes:
        return '{0:.2f} KB'.format(bytes_ / k_bytes)
    elif m_bytes <= bytes_ < g_bytes:
        return '{0:.2f} MB'.format(bytes_ / m_bytes)
    elif g_bytes <= bytes_ < t_bytes:
        return '{0:.2f} GB'.format(bytes_ / g_bytes)
    elif t_bytes <= bytes_:
        return '{0:.2f} TB'.format(bytes_ / t_bytes)


def import_db_data(filename: str) -> Dict[str, List[Any]]:
    """

    :param filename:
    :return:
    """
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = cursor.fetchall()

    output = dict()

    for table_name in table_names:
        cursor.execute("SELECT * FROM " + table_name[0] + ";")

        column_headers = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        data.insert(0, tuple(column_headers))

        output[table_name[0]] = data

    return output


class App(tk.Tk):
    def __init__(self):
        """

        """
        super(App, self).__init__()

        self.title("EnviroPlus: Data Extraction Tool")

        self._window_width = self.winfo_screenwidth()
        self._window_height = self.winfo_screenheight()

        self._width, self._height = 1_000, 600

        self._x = int((self._window_width - self._width) * 0.5)
        self._y = int((self._window_height - self._height) * 0.2)

        geometry_template = "{:d}x{:d}+{:d}+{:d}".format(
            self._width, self._height, self._x, self._y
        )
        self.geometry(geometry_template)

        # Variables
        self.loaded_data = dict()

        # Grid settings
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # Title container
        title_container = ttk.Frame(self)
        title_container.grid(row=0, column=0, sticky=tk.NSEW)

        self.title_template = "Viewing '{0!s}' ({1!s})"
        self.title_label = tk.Label(
            title_container, text="No file opened", font=("Arial Rounded MT Bold", 15)
        )
        self.title_label.pack(anchor=tk.W, padx=5)

        ttk.Separator(title_container, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)

        # Data container
        data_container = ttk.Frame(self)
        data_container.grid(row=1, column=0, sticky=tk.NSEW)

        data_container.rowconfigure(0, weight=0)
        data_container.rowconfigure(1, weight=1)
        data_container.rowconfigure(2, weight=0)
        data_container.columnconfigure(0, weight=1)
        data_container.columnconfigure(1, weight=0)

        self.selected_table = tk.StringVar()
        self.selected_table.trace("w", self.update_table_data)
        self.table_selection = ttk.OptionMenu(data_container, self.selected_table)
        self.table_selection.grid(row=0, column=0, columnspan=3, sticky=tk.NSEW)

        treeview_style = ttk.Style(self)
        treeview_style.configure('Treeview', rowheight=20)
        treeview_style.map('Treeview', background=[('selected', '#86A2A6')], foreground=[('selected', 'white')])

        self.treeview = ttk.Treeview(data_container)
        self.treeview.tag_configure('odd', background='#F0F0F0')
        self.treeview.grid(row=1, column=0, sticky=tk.NSEW)

        x_scrollbar = ttk.Scrollbar(data_container, orient=tk.HORIZONTAL, command=self.treeview.xview)
        y_scrollbar = ttk.Scrollbar(data_container, orient=tk.VERTICAL, command=self.treeview.yview)
        self.treeview.configure(xscrollcommand=x_scrollbar.set, yscrollcommand=y_scrollbar.set)

        x_scrollbar.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW)
        y_scrollbar.grid(row=1, rowspan=2, column=1, sticky=tk.NSEW)

        # Side container
        self.side_container = ttk.Frame(self)
        self.side_container.grid(row=2, column=0, sticky=tk.NSEW)

        temp_container = ttk.Frame(self.side_container)
        temp_container.pack(pady=5, fill=tk.Y)

        ttk.Button(
            temp_container, text="Import from SQLite database", command=self.import_file_dialog
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            temp_container, text="Export selected table to CSV", command=self.save_this_table
        ).pack(side=tk.LEFT, padx=5)

    def import_file_dialog(self) -> None:
        """

        :return:
        """
        filepath = filedialog.askopenfilename(
            title="EnviroPlus: Import from SQLite database",
            filetypes=[("Data Base files", "*.db"), ("All files", "*.*")]
        )

        if filepath:
            file_size = os.path.getsize(filepath)
            self.title_label["text"] = self.title_template.format(filepath.split("/")[-1], get_bytes_string(file_size))

            self.loaded_data = import_db_data(filename=filepath)

            self.update_displayed_data()

    def save_this_table(self) -> None:
        """

        :return:
        """
        if not self.loaded_data:
            messagebox.showerror(
                title="EnviroPlus: Error!",
                message="No file opened. Click the 'Import from SQLite database' button to open a file."
            )
            return

        selected_table = self.selected_table.get()

        filepath = filedialog.asksaveasfilename(
            title="EnviroPlus: Save table as a CSV file", filetypes=[("CSV file", "*.csv")], defaultextension=".csv",
            confirmoverwrite=True, initialfile=selected_table
        )

        if filepath:
            with open(filepath, "w", newline="") as out_file:
                csv_writer = csv.writer(out_file)
                csv_writer.writerows(self.loaded_data[selected_table])

    def update_displayed_data(self) -> None:
        """

        :return:
        """
        table_names = list(self.loaded_data.keys())

        # Update dropdown
        self.table_selection.set_menu(table_names[0], *table_names)

        # Update table
        self.update_table_data()

    def update_table_data(self, *_) -> None:
        """

        :return:
        """
        selected_table = self.selected_table.get()

        self.treeview.delete(*self.treeview.get_children())

        self.treeview["columns"] = self.loaded_data[selected_table][0]
        self.treeview.column("#0", width=0, stretch=tk.NO)

        for column in self.treeview["columns"]:
            self.treeview.column(column, anchor=tk.CENTER)
            self.treeview.heading(column, text=column, anchor=tk.CENTER)

        for i, row in enumerate(self.loaded_data[selected_table][1:]):
            if i % 2 == 0:
                tags = ""
            else:
                tags = "odd"

            self.treeview.insert(parent="", index="end", iid=str(i), text="", tags=tags, values=row)


if __name__ == '__main__':
    App().mainloop()
