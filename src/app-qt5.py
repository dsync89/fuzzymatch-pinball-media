import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QItemDelegate, QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QTableView, QComboBox, QStyledItemDelegate, QLabel
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from PyQt5.QtGui import QPixmap
from fuzzywuzzy import fuzz

import shutil 

DIR1 = "tests\\dir1\\test"
DIR2 = "tests\\dir2\\Clear Logo"
OUT_DIR = "tests\\out"


class ComboBoxDelegate(QItemDelegate):
    # def createEditor(self, parent, option, index):
    #     combo_box = QComboBox(parent)
    #     combo_box.setEditable(True)
    #     combo_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    #     combo_box.setMinimumContentsLength(150)
    #     combo_box.addItems(["Option 1", "Option 2", "Option 3"])
    #     combo_box.currentIndexChanged.connect(self.currentIndexChanged)

    #     return combo_box

    def __init__(self, parent=None, options=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.options = options or []    

    def createEditor(self, parent, option, index):
        combo_box = QComboBox(parent)
        combo_box.setEditable(True)
        combo_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo_box.setMinimumContentsLength(150)

        # Get the row number from the QModelIndex
        row = index.row()

        # Retrieve the detected images string for the corresponding row
        # detected_images_str = self.parent().model().item(row, 2).data(Qt.EditRole)

        detected_images_str = self.options[row]

        # Split the string into a list based on newline characters
        # detected_images = detected_images_str.split('\n')

        # # Add items to the combo box based on the detected images list
        # combo_box.addItems(detected_images)
        # combo_box.addItems(["Option x", "Option y", "Option z"])

        mylist = []
        for item in detected_images_str:
            mylist.append(list(item))

        mylist_str = []
        for item in mylist:
            mylist_str.append(f"{item[1]} | {item[0]}")

        combo_box.addItems(mylist_str)

        combo_box.currentIndexChanged.connect(self.currentIndexChanged)

        return combo_box

    def setEditorData(self, editor, index):
        value = index.model().data(index, role=Qt.DisplayRole)
        editor.setCurrentIndex(editor.findText(value))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), role=Qt.EditRole)

    def currentIndexChanged(self):
        self.commitData.emit(self.sender())
        
class FuzzyMatchApp(QMainWindow):
    def __init__(self):
        super(FuzzyMatchApp, self).__init__()

        self.setWindowTitle("Fuzzy Match App")

        # Variables for directory paths
        self.dir_1_path = DIR1
        self.dir_2_path = DIR2

        # UI Layout
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Buttons to select directories
        select_dir_1_button = QPushButton("Select Dir 1", self)
        select_dir_1_button.clicked.connect(self.browse_dir_1)
        layout.addWidget(select_dir_1_button)

        select_dir_2_button = QPushButton("Select Dir 2", self)
        select_dir_2_button.clicked.connect(self.browse_dir_2)
        layout.addWidget(select_dir_2_button)

        # Button to start fuzzy match
        start_match_button = QPushButton("Start Match", self)
        start_match_button.clicked.connect(self.start_fuzzy_match)
        layout.addWidget(start_match_button)

        # Table View to display fuzzy match results
        self.table_view = QTableView(self)
        layout.addWidget(self.table_view)

        # Add a button for starting the rename process
        start_rename_button = QPushButton("Start Rename", self)
        start_rename_button.clicked.connect(self.start_rename)
        layout.addWidget(start_rename_button)



        central_widget.setLayout(layout)

        # Initialize the table view with an empty model
        self.model = QStandardItemModel(self)
        self.table_view.setModel(self.model)

        self.options_list = {}

        self.options_list[0] = "abc"

        # Set custom delegate for the third column
        combo_box_delegate = ComboBoxDelegate(self.table_view, options=self.options_list)
        self.table_view.setItemDelegateForColumn(2, combo_box_delegate)

        # Set column widths
        self.table_view.setColumnWidth(0, 200)  # Width for the first column
        self.table_view.setColumnWidth(1, 200)  # Width for the second column
        self.table_view.setColumnWidth(2, 700)  # Width for the third column
        

    def browse_dir_1(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Dir 1")
        if directory:
            self.dir_1_path = directory

    def browse_dir_2(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Dir 2")
        if directory:
            self.dir_2_path = directory

    def start_fuzzy_match(self):
        # Perform fuzzy match and update the table view
        fuzzy_match_results = self.perform_fuzzy_match(self.dir_1_path, self.dir_2_path)
        self.update_table_view_with_fuzzy_match(fuzzy_match_results)

    def perform_fuzzy_match(self, dir_1_path, dir_2_path):
        dir_1_files = [file for file in os.listdir(dir_1_path) if file.endswith(".ahk")]
        dir_2_images = [file for file in os.listdir(dir_2_path) if file.endswith((".jpg", ".png"))]

        # Remove file extensions
        dir_1_files = [os.path.splitext(file)[0] for file in dir_1_files]
        dir_2_images = [os.path.splitext(file)[0] for file in dir_2_images]

        fuzzy_match_results = []

        for file_1 in dir_1_files:
            best_match = max(dir_2_images, key=lambda file_2: fuzz.ratio(file_1, file_2))
            detected_images = [(file, fuzz.ratio(file_1, file)) for file in dir_2_images if fuzz.ratio(file_1, file) >= 10]

            fuzzy_match_results.append((file_1, best_match, detected_images))

        return fuzzy_match_results

    def update_table_view_with_fuzzy_match(self, fuzzy_match_results):
        self.model.clear()
        self.model.setColumnCount(3)
        self.model.setHorizontalHeaderLabels([".ahk Filename", "Fuzzy Matched Image", "Detected Images"])
        # self.setItemDelegateForColumn(2, ComboBoxDelegate())

        # self.hashmap = {}

        for index, result in enumerate(fuzzy_match_results):
            item_1 = QStandardItem(result[0])
            item_2 = QStandardItem(result[1])
            item_3 = QStandardItem(result[1])

            # Create combo box for the third column
            # combo_box = QComboBox()
            # combo_box.setEditable(True)
            # combo_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            # combo_box.setMinimumContentsLength(150)

            detected_images = []

            for file, ratio in result[2]:
                # combo_box.addItem(f"{file}: {ratio}")
                # detected_images.append(f"{file}: {ratio}")

                detected_images.append( (file, ratio) )

            detected_images_sorted_data = sorted(detected_images, key=lambda x: x[1], reverse=True)
            self.options_list[index] = detected_images_sorted_data

            # # Set the combo box as data for the third column item
            # item_3 = QStandardItem()
            # item_3.setData(combo_box, Qt.EditRole)

            # Append the items to the model
            self.model.appendRow([item_1, item_2, item_3])

            # self.model.setItem(item_1, item_2, combo_box)

        self.table_view.setModel(self.model)

    def get_column_values(self, col_idx):
        # Get all the currently displayed values in column 2
        column_values = []

        for row in range(self.model.rowCount()):
            item = self.model.item(row, col_idx)  # Column 2

            if item is not None:
                column_values.append(item.text())

        print("Column values:", column_values)      
        return column_values    

    def start_rename(self):
        # Implement your renaming logic here
        print("Start Rename button clicked!")

        # Get all the currently displayed values in each column
        column_1_values = self.get_column_values(0)
        column_2_values = self.get_column_values(1)
        column_3_values = self.get_column_values(2)

        # start rename
        for index, filename in enumerate(column_3_values):
            # split the ratio, text
            if '|' in filename:
                parts = filename.split('|')
                filename = parts[1].strip()

            ahk_filename, ahk_file_extension = os.path.splitext(column_1_values[index])
            img_filename, img_file_extension = os.path.splitext(filename)



            src_file = os.path.join(DIR2, filename)
            dest_file = os.path.join(OUT_DIR, f"{ahk_filename}{img_file_extension}")
            print(f"Copying [ {src_file} ] => [ {dest_file} ]")      
            shutil.copy2(src_file, dest_file)

def main():
    app = QApplication([])
    window = FuzzyMatchApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()