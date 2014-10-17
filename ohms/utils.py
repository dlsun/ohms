import json
from datetime import datetime
from objects import QuestionResponse, ItemResponse

# special JSON encoder to handle dates and Response objects
class NewEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return datetime.strftime(obj, "%m/%d/%Y %H:%M:%S")
        elif isinstance(obj, QuestionResponse):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            d['item_responses'] = obj.item_responses
            return d
        elif isinstance(obj, ItemResponse):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            return d
        return json.JSONEncoder.default(self, obj)

def convert_to_last_name(name):
    x = name.split()
    if x[-1] not in ["I", "II", "III", "Jr.", "Sr.", "Jr", "Sr"]:
        return x[-1] + ', ' + " ".join(x[:-1])
    else:
        return " ".join(x[-2:]) + ',' + " ".join(x[:-2])
