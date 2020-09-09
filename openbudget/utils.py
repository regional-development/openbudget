import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List


RAW_FILES = Path(__file__).resolve().parent.parent / "data" / "api_response"
PROCESSED = Path(__file__).resolve().parent.parent / "data" / "tables"
DTYPE_INC = {
    "ADMIN": str,
    "FIN_SOURCE": str,
    "INCO": str,
    "ADJUSTED": float, 
    "EXECUTED": float,
    "DATE": str
}
DTYPE_EXP  = {
    "ADMIN": str,
    "FIN_SOURCE": str,
    "PROG": str,
    "FUNC": str,
    "ECON": str,
    "ADJUSTED": float, 
    "EXECUTED": float,
    "EXECUTED_FIN_SOURCE_n1": float,
    "EXECUTED_FIN_SOURCE_n2": float,
    "EXECUTED_FIN_SOURCE_n6": float,
    "IS_CUMULATIVE": str,
    "DATE": str
}


def get_cumulative(
    files: List[Dict[str, Any]], 
    item_type: str ="EXPENSES"
) -> Dict[int, pd.DataFrame]:
    """ Перетворює щомісячні json на словник датафреймів. 
    Значення залишаються кумулятивними.
    
    
    Parameters
    ----------
        files : List[JSON]
            Відповідь АРІ openbudget.
        item_type : str
            Маркер типу файлу (видатки / доходи)
    """
    
    _mappings = {
        "01": 1,
        "02": 2,
        "03": 3,
        "04": 4,
        "05": 5,
        "06": 6,
        "07": 7,
        "08": 8,
        "09": 9,
        "10": 10,
        "11": 11,
        "12": 12
    }
    
    d = dict()
    for file in files:        
        with open(file, "r") as f:
            data = json.load(f)
        
        month_string = str(file).split("/")[-1].split("_")[-1].split(".")[0]
        month = _mappings.get(month_string)
        
        df = pd.json_normalize(data)
        df["MONTH"] = month
        
        if item_type == "EXPENSES":
            df["IS_CUMULATIVE"] = df["ECON"].eq("0000").astype(int)
        
        d[month] = df.drop_duplicates()
    
    return d


def transform(
    d: Dict[int, pd.DataFrame], 
    item_type: str,
    year: str
) -> pd.DataFrame:
    """Перетворює словник датафреймів на єдину таблицю та 
    перетворює кумулятивні значення на некумулятивні щомісячні
    
    
    Parameters
    ----------
        d : Dict[int, pd.DataFrame]
            Словник датафреймів з кумулятивними значеннями
        item_type : str
            Маркер типу файлу (видатки / доходи)
    """
    
    current_range = list(d.keys())[::-1]
    previous_range = [m-1 for m in current_range]
    
    if item_type == "EXPENSES":
        idxs = ["ADMIN", "FIN_SOURCE", "PROG", "FUNC", "ECON"]
    else:
        idxs = ["ADMIN", "FIN_SOURCE", "INCO"]
    
    data = dict()
    for current, previous in zip(current_range, previous_range):
        if previous != 0:

            tmp = (
                d[current].set_index(idxs).subtract(d[previous].set_index(idxs), fill_value=0)
            )
            ac = (
                d[current].set_index(idxs)["ADJUSTED"]
            )
            # cumulative
            tmp["ADJUSTED"] = tmp.index.map(ac.to_dict())
            
            table = tmp.reset_index()
            table["MONTH"] = current
             
            if item_type == "EXPENSES":
                table["IS_CUMULATIVE"] = table["ECON"].eq("0000").astype(int)
            
            data[current] = table
        else:
            data[current] = d[1]
    
    df = pd.concat([*data.values()], ignore_index=False)[::-1]
    df["DATE"] = pd.to_datetime(
        year + " " + df["MONTH"].astype(str) + " 01"
    ).dt.strftime("%Y-%m-%d")
    
    return df.drop("MONTH", 1)