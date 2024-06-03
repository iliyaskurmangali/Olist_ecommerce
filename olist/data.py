import os
import pandas as pd



class Olist:
    def get_data(self):
        """
        This function returns a Python dict.
        Its keys should be 'sellers', 'orders', 'order_items' etc...
        Its values should be pandas.DataFrames loaded from csv files
        """

        # Hints 1: Build csv_path as "absolute path" in order to call this method from anywhere.
            # Do not hardcode your path as it only works on your machine ('Users/username/code...')
            # Use __file__ instead as an absolute path anchor independant of your usename
            # Make extensive use of `breakpoint()` to investigate what `__file__` variable is really
        # Hint 2: Use os.path library to construct path independent of Mac vs. Unix vs. Windows specificities
        dir_path = os.path.dirname(os.path.dirname(__file__))
        csv_path = os.path.join(dir_path, "data/csv")
        print(csv_path)
        file_names=[x for x in os.listdir(csv_path) if x.endswith('.csv')]
        key_names=[]
        for i in file_names:
            if '.csv' in i:
                i=i.replace('.csv','').replace('olist_','').replace("_dataset",'')
                key_names.append(i)
            else:
                key_names.append(i)
        data={}
        for  (x,y) in zip(file_names, key_names):
            data[y]=pd.read_csv(csv_path+'/'+x)
        return data
    def ping(self):
        """
        You call ping I print pong.
        """
        print("pong")
