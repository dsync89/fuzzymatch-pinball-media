import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QItemDelegate, QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QTableView, QComboBox, QStyledItemDelegate, QLabel, QFrame, QHBoxLayout, QLineEdit, QProgressBar, QHeaderView, QRadioButton, QDialog, QGridLayout, QStyleOptionViewItem
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush

from PyQt5.QtGui import QPixmap
from fuzzywuzzy import fuzz

import shutil 
import re

import debugpy

debugpy.listen(('localhost', 5678))

# DIR1 = "r:\\ROMS-1G1R\\pinball\\Visual Pinball\\test"
# DIR2 = "c:\\PinUPSystem\\POPMedia\\Visual Pinball X\\Audio"
OUT_DIR = "tests\\out"

class ImagePopupDialog(QDialog):
    def __init__(self, options, DIR2, parent=None):
        super(ImagePopupDialog, self).__init__(parent)
        self.options = options
        self.selected_option = None
        self.DIR2 = DIR2

        self.setWindowTitle("Select Image")
        self.setGeometry(200, 200, 600, 400)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        grid_layout = QGridLayout()
        self.radio_buttons = []

        # add a dummy empty option to the beginning so that user can choose none
        if len(self.options) > 0:
            
            if self.options[0] != "":
                self.options.insert(0, "")

            # Iterate through options and create grid layout (left to right, 5 item per row)
            for i, option in enumerate(self.options[:10]):
                row = i // 5
                col = i % 5

                cell_layout = QVBoxLayout()

                if i == 0: # the first item
                    img_label = QLabel(self)
                    img_path = os.path.join("assets", "no-image.jpg")
                    pixmap = QPixmap(img_path).scaledToWidth(100)
                    img_label.setPixmap(pixmap)
                    img_label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

                    radio_button = QRadioButton(" ")
                    radio_button.setChecked(False)

                else:
                    img_label = QLabel(self)
                    img_path = os.path.join(self.DIR2, option[0])
                    pixmap = QPixmap(img_path).scaledToWidth(100)
                    img_label.setPixmap(pixmap)
                    img_label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

                    radio_button = QRadioButton(option[0] + f"[{option[1]}]") # print image name + ratio
                    radio_button.setChecked(False)

                cell_layout.addWidget(img_label)
                cell_layout.addWidget(radio_button)
                cell_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

                grid_layout.addLayout(cell_layout, row, col)

                self.radio_buttons.append(radio_button)

        layout.addLayout(grid_layout)

        select_button = QPushButton("Select Image", self)
        select_button.clicked.connect(self.select_image)
        layout.addWidget(select_button)

        self.setLayout(layout)

    def select_image(self):
        for radio_button in self.radio_buttons:
            if radio_button.isChecked():
                # return the selected radio button text withou the [ratio]

                if '[' in radio_button.text():
                    last_bracket_index = radio_button.text().rfind('[')

                    # Extract text from the first character until the last '['
                    self.selected_option = radio_button.text()[:last_bracket_index]

                else:
                    self.selected_option = radio_button.text()
                self.accept()

class FuzzyMatchThread(QThread):
    progressUpdated = pyqtSignal(int)
    fileProcessed = pyqtSignal(str)
    resultReady = pyqtSignal(object)


    def __init__(self, parent=None):
        super(FuzzyMatchThread, self).__init__(parent)
        self.dir_1_path = ""
        self.dir_2_path = ""

    def setDirectories(self, dir_1_path, dir_2_path):
        self.dir_1_path = dir_1_path
        self.dir_2_path = dir_2_path

    def run(self):
        debugpy.breakpoint()
        fuzzy_match_results = self.perform_fuzzy_match(self.dir_1_path, self.dir_2_path)
        self.progressUpdated.emit(100)  # Signal completion
        self.resultReady.emit(fuzzy_match_results)

    def gen_file_tuples(self, dir_1_files):
        dir_1_files_tuples = [] # (filename_without_ext, regexed_filename_without_ext, filename_with_ext)

        for file in dir_1_files:
            basename = os.path.splitext(file)[0]
            match = re.search(r'^[^(\[]+', basename)

            if match:
                regexed_basename = match.group(0)
            else:
                regexed_basename = basename    

            dir_1_files_tuples.append((basename, regexed_basename, file))
        
        return dir_1_files_tuples    

    def perform_fuzzy_match(self, dir_1_path, dir_2_path):
        dir_1_files = [file for file in os.listdir(dir_1_path) if file.endswith(".ahk")]
        dir_2_images = [file for file in os.listdir(dir_2_path) if file.endswith((".jpg", ".png", ".mp3", ".mp4", ".f4v"))]

        # dir_1_files_filenames = [os.path.splitext(file)[0] for file in dir_1_files]
        # dir_2_images_filenames = [os.path.splitext(file)[0] for file in dir_2_images]

        dir_1_files_tuples = self.gen_file_tuples(dir_1_files) # (filename_without_ext, regexed_filename_without_ext, filename_with_ext)
        dir_2_images_tuples = self.gen_file_tuples(dir_2_images) # (filename_without_ext, regexed_filename_without_ext, filename_with_ext)

        fuzzy_match_results = []

        total_files = len(dir_1_files)
        processed_files = 0

        for file_1 in dir_1_files_tuples:
            # find best match
            best_match = max(dir_2_images_tuples, key=lambda file_2: fuzz.ratio(file_1[1], file_2[1]))

            # generate tuple (filename, ratio)
            detected_images = []
            for file in dir_2_images_tuples:
                ratio = fuzz.ratio(file_1[1], file[1])

                if ratio >= 50:
                    detected_images.append((file[2], ratio))

            fuzzy_match_results.append((file_1[2], best_match, detected_images))

            processed_files += 1
            progress_percentage = int(processed_files / total_files * 100)
            self.progressUpdated.emit(progress_percentage)
            self.fileProcessed.emit(file_1[2])

        return fuzzy_match_results

class ComboBoxDelegate(QItemDelegate):
    def __init__(self, parent=None, options=None, DIR2=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.options = options or []
        self.DIR2 = DIR2  # Store DIR2 as an instance variable

    def set_DIR2(self, DIR2):
        self.DIR2 = DIR2        

    def createEditor(self, parent, option, index):
        button = QPushButton("Select Image", parent)
        button.clicked.connect(lambda _, index=index: self.open_popup_dialog(index))

        return button

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass

    def open_popup_dialog(self, index):
        options = self.options.get(index.row(), [])
        dialog = ImagePopupDialog(options, self.DIR2, self.parent())

        if dialog.exec_() == QDialog.Accepted:
            selected_option = dialog.selected_option
            if selected_option:
                index.model().setData(index, selected_option, role=Qt.EditRole)
                index.model().layoutChanged.emit()

    # def paint(self, painter, option, index):
    #     super().paint(painter, option, index)

    #     # Check if the text in the third column contains 'abc'
    #     if index.column() == 2 and '24' in index.data(Qt.DisplayRole):
    #         # Highlight the item by drawing a colored background
    #         option = QStyleOptionViewItem(option)
    #         option.palette.setColor(option.palette.Highlight, QColor(255, 255, 0))  # Yellow color
    #         option.palette.setColor(option.palette.HighlightedText, QColor(0, 0, 0))  # Black color
    #         self.drawBackground(painter, option, index)                

    def data(self, index, role):
        if role == Qt.BackgroundRole and index.column() == 2 and '24' in index.data(Qt.DisplayRole):
            return QBrush(QColor(255, 255, 0))  # Yellow color
        return super().data(index, role)

class FuzzyMatchApp(QMainWindow):
    progressUpdated = pyqtSignal(int)
    fileProcessed = pyqtSignal(str)
    resultReady = pyqtSignal(object)

    def __init__(self):
        super(FuzzyMatchApp, self).__init__()

        self.setWindowTitle("Fuzzy Match App")
        self.setGeometry(100, 100, 1280, 720)

        self.dir_1_path = ""
        self.dir_2_path = ""
        self.DIR1 = ""
        self.DIR2 = ""     

        self.fuzzy_thread = FuzzyMatchThread()
        self.fuzzy_thread.resultReady.connect(self.update_table_view_with_fuzzy_match)
        self.fuzzy_thread.progressUpdated.connect(self.update_progress_bar)
        self.fuzzy_thread.fileProcessed.connect(self.update_status_label)

                
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()

        # Left frame
        left_frame = QFrame(self)
        left_frame.setFixedWidth(500)  # Set the minimum width
        left_layout = QVBoxLayout(left_frame)
        left_layout.setAlignment(Qt.AlignTop)

        # Pair 1: Dir 1 Label and Button
        pair_1_layout = QHBoxLayout()
        dir_1_label = QLabel("Dir 1 Path:", left_frame)
        dir_1_chosen_textfield = QLineEdit("", left_frame)  # New text field to display chosen dir path
        dir_1_chosen_textfield.setReadOnly(False)  # allow user to paste its path
        select_dir_1_button = QPushButton("...", left_frame)
        select_dir_1_button.clicked.connect(self.browse_dir_1)
        select_dir_1_button.setFixedSize(20, select_dir_1_button.sizeHint().height())
        pair_1_layout.addWidget(dir_1_label)
        pair_1_layout.addWidget(dir_1_chosen_textfield)  # Add the new label
        pair_1_layout.addWidget(select_dir_1_button)
        left_layout.addLayout(pair_1_layout)

        # Pair 2: Dir 2 Label and Button
        pair_2_layout = QHBoxLayout()
        dir_2_label = QLabel("Dir 2 Path:", left_frame)
        dir_2_chosen_textfield = QLineEdit("", left_frame)  # New text field to display chosen dir path
        dir_2_chosen_textfield.setReadOnly(False)  # allow user to paste its path
        select_dir_2_button = QPushButton("...", left_frame)
        select_dir_2_button.clicked.connect(self.browse_dir_2)
        select_dir_2_button.setFixedSize(20, select_dir_2_button.sizeHint().height())
        pair_2_layout.addWidget(dir_2_label)
        pair_2_layout.addWidget(dir_2_chosen_textfield)
        pair_2_layout.addWidget(select_dir_2_button)  # Add the new label
        left_layout.addLayout(pair_2_layout)

        # Button to start fuzzy match
        start_match_button = QPushButton("Start Match", left_frame)
        start_match_button.clicked.connect(self.start_fuzzy_match)
        left_layout.addWidget(start_match_button)

        # Status label
        self.status_label = QLabel("Processing...", left_frame)
        left_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar(left_frame)
        left_layout.addWidget(self.progress_bar)  

        # Statistics label
        self.statistics_label = QLabel("Statistics: 0 empty cells in Column 3", left_frame)
        left_layout.addWidget(self.statistics_label)              

        layout.addWidget(left_frame)
        

        # add to self so that other class can refer
        self.leftframe_dir_1_chosen_textfield = dir_1_chosen_textfield
        self.leftframe_dir_2_chosen_textfield = dir_2_chosen_textfield

        # --------------

        # Right frame
        right_frame = QFrame(self)
        right_layout = QVBoxLayout(right_frame)

        self.table_view = QTableView(self)
        right_layout.addWidget(self.table_view)

        start_rename_button = QPushButton("Start Rename", right_frame)
        start_rename_button.clicked.connect(self.start_rename)
        right_layout.addWidget(start_rename_button)

        layout.addWidget(right_frame)

        central_widget.setLayout(layout)

        # Initialize the table view with an empty model
        self.model = QStandardItemModel(self)
        self.table_view.setModel(self.model)

        self.options_list = {}

        # must initialize at least one
        self.options_list[0] = "zzz"

        # Set custom delegate for the third column
        combo_box_delegate = ComboBoxDelegate(self.table_view, options=self.options_list, DIR2=self.DIR2)
        self.table_view.setItemDelegateForColumn(2, combo_box_delegate)

        # Set column widths
        for col in range(self.model.columnCount()):
            self.table_view.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        # Set the last section to stretch, ensuring it fills the remaining width
        self.table_view.horizontalHeader().setStretchLastSection(True)

        # Set column widths
        self.table_view.setColumnWidth(0, 200)
        self.table_view.setColumnWidth(1, 200)
        # self.table_view.setColumnWidth(2, 400)

    def show_directory_error_dialog(self):
        error_dialog = QDialog(self)
        error_dialog.setWindowTitle("Directory Error")
        error_dialog.setGeometry(300, 300, 400, 100)

        layout = QVBoxLayout()

        error_label = QLabel("One or both of the selected directories are invalid or do not exist.")
        layout.addWidget(error_label)

        ok_button = QPushButton("OK", error_dialog)
        ok_button.clicked.connect(error_dialog.accept)
        layout.addWidget(ok_button)

        error_dialog.setLayout(layout)
        error_dialog.exec_()        

    def start_fuzzy_match(self):
        # check if dir is valid, it not display error as popup dialog
        dir_1_path = self.leftframe_dir_1_chosen_textfield.text()
        dir_2_path = self.leftframe_dir_2_chosen_textfield.text()

        if not os.path.isdir(dir_1_path) or not os.path.isdir(dir_2_path):
            self.show_directory_error_dialog()
            return        
        
        self.progress_bar.setValue(0)  # Reset progress bar
        self.status_label.setText("Processing...")

        self.fuzzy_thread.setDirectories(dir_1_path, dir_2_path)
        self.fuzzy_thread.start()        

        self.DIR1 = dir_1_path
        self.DIR2 = dir_2_path

        # update comboboxdelgate
        combo_box_delegate = self.table_view.itemDelegateForColumn(2)
        if combo_box_delegate:
            combo_box_delegate.set_DIR2(self.DIR2)

    def update_status_label(self, filename):
        if len(filename) > 50:
            filename = filename[:47] + "..."  # Display only the first 47 characters and add ellipsis
        self.status_label.setText(f"Processing: {filename}")   

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)        

    def browse_dir_1(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Dir 1")
        if directory:
            self.dir_1_path = directory
            self.leftframe_dir_1_chosen_textfield.setText(directory)  # Update the label text

    def browse_dir_2(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Dir 2")
        if directory:
            self.dir_2_path = directory
            self.leftframe_dir_2_chosen_textfield.setText(directory)  # Update the label text

    # def start_fuzzy_match(self):
    #     fuzzy_match_results = self.perform_fuzzy_match(self.dir_1_path, self.dir_2_path)
    #     self.update_table_view_with_fuzzy_match(fuzzy_match_results)

    def perform_fuzzy_matc2(self, dir_1_path, dir_2_path):
        dir_1_files = [file for file in os.listdir(dir_1_path) if file.endswith(".ahk")]
        dir_2_images = [file for file in os.listdir(dir_2_path) if file.endswith((".jpg", ".png"))]

        dir_1_files = [os.path.splitext(file)[0] for file in dir_1_files]
        dir_2_images = [os.path.splitext(file)[0] for file in dir_2_images]

        fuzzy_match_results = []

        total_files = len(dir_1_files)
        processed_files = 0

        for file_1 in dir_1_files:
            best_match = max(dir_2_images, key=lambda file_2: fuzz.ratio(file_1, file_2))
            detected_images = [(file, fuzz.ratio(file_1, file)) for file in dir_2_images if fuzz.ratio(file_1, file) >= 10]

            fuzzy_match_results.append((file_1, best_match, detected_images))

            processed_files += 1
            progress_percentage = int(processed_files / total_files * 100)
            self.progressUpdated.emit(progress_percentage)
            self.fileProcessed.emit(file_1)

        return fuzzy_match_results


    def update_table_view_with_fuzzy_match(self, fuzzy_match_results):
        self.model.clear()
        self.model.setColumnCount(4)
        self.model.setHorizontalHeaderLabels([".ahk Filename", "Fuzzy Matched Image", "Detected Images", "Chosen Image"])

        empty_cells_count = 0  # Counter for empty cells in column 3        
        total_rows_column_1 = 0  # Counter for total rows in column 1

        for index, result in enumerate(fuzzy_match_results):
            item_1 = QStandardItem(result[0])
            item_2 = QStandardItem(result[1][2])
            item_3 = QStandardItem(result[1][2])

            total_rows_column_1 += 1  # Increment count for total rows in column 1

            detected_images = []

            for file, ratio in result[2]:
                # if ratio > 40:
                detected_images.append((file, ratio))

            detected_images_sorted_data = sorted(detected_images, key=lambda x: x[1], reverse=True)
            self.options_list[index] = detected_images_sorted_data

            # Add the chosen image as the 4th column
            chosen_image_filename = result[1][2]  # Assuming result[1] is the chosen image filename
            chosen_image_item = QStandardItem()
            chosen_image_path = os.path.join(self.DIR2, chosen_image_filename)
            pixmap = QPixmap(chosen_image_path).scaledToWidth(100)
            chosen_image_item.setData(pixmap, Qt.DecorationRole)    

            # colorize
            try:
                if detected_images_sorted_data[0][1] >= 100:
                    item_3.setBackground(QBrush(QColor(0, 255, 0))) 
                elif detected_images_sorted_data[0][1] >= 80:
                    item_3.setBackground(QBrush(QColor(0, 200, 0))) 
                elif detected_images_sorted_data[0][1] >= 65:
                    item_3.setBackground(QBrush(QColor(255, 255, 0))) # yellow
                elif detected_images_sorted_data[0][1] < 65:
                    item_3 = QStandardItem("")
                    empty_cells_count += 1  # Increment count for empty cells

            except Exception as e:
                print(f"An error occurred: {e}") 
                item_3 = QStandardItem("")        
                empty_cells_count += 1  # Increment count for empty cells        

            self.model.appendRow([item_1, item_2, item_3, chosen_image_item])

        # Update the statistics label
        total_matched_cells = total_rows_column_1 - empty_cells_count
        percentage_matched_cells = int ( ( total_matched_cells / total_rows_column_1 ) * 100 ) 
        self.statistics_label.setText(f"Statistics: {total_matched_cells} / {total_rows_column_1} [{percentage_matched_cells}%] matched cells in Column 3")

        self.table_view.setModel(self.model)

    def start_rename(self):
        print("Start Rename button clicked!")

        column_1_values = self.get_column_values(0)
        column_2_values = self.get_column_values(1)
        column_3_values = self.get_column_values(2)

        for index, filename in enumerate(column_3_values):
            if len(filename.strip()) == 0:
                continue

            if '|' in filename:
                parts = filename.split('|')
                filename = parts[1].strip()

            ahk_filename, ahk_file_extension = os.path.splitext(column_1_values[index])
            img_filename, img_file_extension = os.path.splitext(filename)

            src_file = os.path.join(self.DIR2, filename)
            dest_file = os.path.join(OUT_DIR, f"{ahk_filename}{img_file_extension}")
            print(f"Copying [ {src_file} ] => [ {dest_file} ]")
            shutil.copy2(src_file, dest_file)

    def get_column_values(self, col_idx):
        column_values = []

        for row in range(self.model.rowCount()):
            item = self.model.item(row, col_idx)

            if item is not None:
                column_values.append(item.text())

        print("Column values:", column_values)
        return column_values

def main():
    app = QApplication([])
    window = FuzzyMatchApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()