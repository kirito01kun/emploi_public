import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QScrollArea, QHBoxLayout, QComboBox
)
from PyQt5.QtGui import QMovie, QFont
from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal
import sys
import webbrowser
from PyQt5.QtCore import QDir


# Constants
BASE_URL = "https://www.emploi-public.ma/FR/index.asp"
JOB_DETAIL_BASE_URL = "https://www.emploi-public.ma/FR/"
today = datetime.now().strftime("%d/%m/%Y")

class JobScraperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Window settings
        self.setGeometry(100, 100, 600, 600)
        self.setWindowTitle("Job Scraper App")
        self.setStyleSheet("background-color: #2c3e50; font-family: Arial, sans-serif;")

        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # Keyword input
        self.keyword_label = QLabel("Enter keywords to search:")
        self.keyword_label.setStyleSheet("color: #ecf0f1; font-size: 18px; font-weight: bold;")
        self.keyword_entry = QLineEdit()
        self.keyword_entry.setPlaceholderText("e.g., Echelle, grade, ville...")
        self.keyword_entry.setStyleSheet(self.get_input_style())

        # Date selection
        self.date_label = QLabel("Select date range:")
        self.date_label.setStyleSheet("color: #ecf0f1; font-size: 18px; font-weight: bold;")
        self.date_selector = QComboBox()
        self.date_selector.addItems(["Today", "Yesterday", "Last Week"])
        self.date_selector.setStyleSheet(self.get_combo_style())

        # Start button
        self.start_button = QPushButton("Get Links")
        self.start_button.setStyleSheet(self.get_button_style())
        self.start_button.clicked.connect(self.start_scraping)

        
        # Scroll Area for job buttons
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(250)  # Set fixed height for the scroll area
        self.scroll_area.setStyleSheet("border: none;")  # Remove default border

        # Container widget for buttons
        self.button_container = QWidget()
        self.button_layout = QVBoxLayout(self.button_container)  # Layout for buttons
        self.button_container.setLayout(self.button_layout)

        self.scroll_area.setWidget(self.button_container)

        # Horizontal layout for button and loading icon
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.setAlignment(Qt.AlignCenter)

        # Add widgets to layout
        layout.addWidget(self.keyword_label)
        layout.addWidget(self.keyword_entry)
        layout.addWidget(self.date_label)
        layout.addWidget(self.date_selector)
        layout.addLayout(button_layout)
        layout.addWidget(self.scroll_area)

        # Copyright section
        copyright_label = QLabel("© 2024 ykbala")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #bdc3c7; margin-top: 20px; font-size: 12px;")
        layout.addWidget(copyright_label)

        # Set layout
        self.setLayout(layout)

    def get_input_style(self):
        return """
            QLineEdit {
                padding: 12px;
                border: 1px solid #ecf0f1;
                border-radius: 10px;
                font-size: 14px;
                color: #34495e;
                background-color: #ecf0f1;
            }
            QLineEdit::placeholder {
                color: #95a5a6;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
                background-color: #f0f8ff;
            }
        """

    def get_combo_style(self):
        return """
            QComboBox {
                padding: 12px;
                border: 2px solid #3498db;
                border-radius: 8px;
                font-size: 16px;
                background-color: #ecf0f1;
                color: #2c3e50;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #2980b9;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: #3498db;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox::down-arrow {
                image: url(down-arrow.png);  /* Replace with your arrow icon if available */
                width: 14px;
                height: 14px;
            }
        """

    def get_button_style(self):
        return """
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px 25px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """

    def open_link(self, url):
        webbrowser.open(url)

    def start_scraping(self):
        # Clear previous buttons
        for i in reversed(range(self.button_layout.count())): 
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        self.results_found = False
        self.start_button.setEnabled(False)

        keywords = self.keyword_entry.text().split(',')
        keywords = [kw.strip() for kw in keywords if kw.strip()]

        if not keywords:
            QMessageBox.warning(self, "Error", "Please enter at least one keyword.")
            return

        # Get the selected date
        selected_date = self.date_selector.currentText()
        if selected_date == "Today":
            self.start_date = datetime.now()
        elif selected_date == "Yesterday":
            self.start_date = datetime.now() - timedelta(days=1)
        elif selected_date == "Last Week":
            self.start_date = datetime.now() - timedelta(days=7)

        # Calculate the end date
        self.end_date = self.start_date.strftime("%d/%m/%Y")

        # Start scraping in a separate thread to keep UI responsive
        self.scraper_thread = ScraperThread(keywords, self.start_date, self.end_date)
        self.scraper_thread.results_signal.connect(self.display_result)
        self.scraper_thread.page_signal.connect(self.update_loading_text)
        self.scraper_thread.finished.connect(self.on_scraping_finished)
        self.scraper_thread.start()

    def display_result(self, job_detail_url, job_title):
        self.results_found = True
        # Create a button for each job link
        button = QPushButton(job_title)
        button.setStyleSheet("width: 100%; text-align: left; padding: 10px; font-size: 14px; background-color: #ecf0f1; border-radius: 5px;")
        button.clicked.connect(lambda: webbrowser.open(job_detail_url))  # Open the link on click
        self.button_layout.addWidget(button)  # Add button to the layout
        self.button_layout.addStretch()  # Add stretchable space

    def update_loading_text(self, page):
        self.start_button.setText(f"Searching... (page {page})")        

    def on_scraping_finished(self):
        if not self.results_found:
            button = QPushButton("Nothing found !")
            button.setStyleSheet("width: 100%; text-align: left; padding: 10px; font-size: 14px; background-color: #ecf0f1; border-radius: 5px;")
            self.button_layout.addWidget(button)  # Add button to the layout
            self.button_layout.addStretch() 
        self.keyword_entry.clear()
        self.start_button.setText("Get Links")
        self.start_button.setEnabled(True)
    


# Worker thread for scraping
class ScraperThread(QThread):
    results_signal = pyqtSignal(str, str)  # Emit job URL and title
    page_signal = pyqtSignal(int)

    def __init__(self, keywords, start_date, end_date):
        super().__init__()
        self.keywords = keywords
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        fetch_job_listings(self.keywords, self.start_date, self.end_date, self.results_signal, self.page_signal)


# Scraping functions
def fetch_job_listings(keywords, start_date, end_date, signal, page_signal):
    page_number = 1
    while True:
        # Construct URL with page number
        url = f"{BASE_URL}?p={page_number}"
        page_signal.emit(page_number)
        response = requests.get(url)
        response.encoding = 'utf-8'  # Set encoding to utf-8
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the table containing job listings
        job_table = soup.find("table", class_="table table-sm table-striped")
        if not job_table:
            break

        # Process each row in the table (excluding header row)
        rows = job_table.find_all("tr")[1:]  # Skip header row
        date_found = False  # Flag to check if we have found a valid date
        for row in rows:
            columns = row.find_all("td")
            if len(columns) == 3:
                # Extract date and job title from each row
                date_posted = columns[1].text.strip()
                # Check if the date matches the selected date
                if date_posted == end_date:
                    date_found = True  # We found a valid date
                elif date_found and date_posted != end_date:
                    # If we found a date previously and now we encounter a different date, we can stop scraping
                    return

                # Extract the job details link from the <a> tag inside the third <td>
                job_link_tag = columns[2].find("a")
                job_detail_url = JOB_DETAIL_BASE_URL + job_link_tag["href"]
                job_title = job_link_tag.text.strip()

                # Visit the job details page and check if it matches any search keyword
                if check_job_details(job_detail_url, keywords):
                    # Emit the job link and title for display
                    signal.emit(job_detail_url, job_title)

        # Go to the next page
        page_number += 1

def check_job_details(job_url, keywords):
    # Request the job details page
    response = requests.get(job_url)
    response.encoding = 'utf-8'
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the detailed table on the job page
    details_table = soup.find("table", class_="table table-striped table-bordered table-sm")
    if details_table:
        # Check the first four rows in the table for any of the keywords
        for index, row in enumerate(details_table.find_all("tr")):
            if index >= 4:  # Check only the first four rows
                break
            row_text = row.get_text().lower()
            for keyword in keywords:
                if keyword.lower() in row_text:
                    return True
    return False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = JobScraperApp()
    window.show()
    sys.exit(app.exec_())
