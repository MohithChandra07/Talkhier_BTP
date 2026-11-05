import pandas as pd
import os

class ResultManager:

    def __init__(self, file_path, columns=["Problem ID", "Answer", "Correct Answer", "Pre-Revision"]):
        self.file_path = file_path
        self.columns = columns
        self.results_list = []
    

    def loadFile(self):
        if os.path.exists(self.file_path):
            self.results_list = pd.read_csv(self.file_path).values.tolist()
        else:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            self.results_list = []
    
    def saveFile(self):
        pd.DataFrame(self.results_list, columns=self.columns).to_csv(self.file_path, index=False)
    

    def add(self, data):
        self.loadFile()
        self.results_list.append(data)
        self.saveFile()
    
    def remove(self, data):
        self.loadFile()
        if data in self.results_list:
            self.results_list.remove(data)
            self.saveFile()
        else:
            filtered = [row for row in self.results_list if str(row[0]) != str(data[0])]
            if len(filtered) != len(self.results_list):
                self.results_list = filtered
                self.saveFile()
    
    def replace(self, data_from, data_to):
        self.loadFile()
        if data_from in self.results_list:
            self.results_list.remove(data_from)
        else:
            self.results_list = [row for row in self.results_list if str(row[0]) != str(data_to[0])]
        self.results_list.append(data_to)
        self.saveFile()
    

    def is_present(self, data, axis=0):
        self.loadFile()
        for read_data in self.results_list:
            if str(read_data[axis]) == str(data[axis]):
                if len(read_data) > 1 and str(read_data[1]) != '-':
                    return True
        return False