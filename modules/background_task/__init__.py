import atexit
from datetime import datetime
from threading import Thread

import pymongo
from apscheduler.schedulers.background import BlockingScheduler, BackgroundScheduler

from modules.background_task.sliding_window_method import sliding_window
from modules.background_task.variance_method import variance_method
from modules.config import Config


def get_data_in_interval(mongo_resource, start, end):
    print("Getting data")
    try:
        cursor = mongo_resource.find({
            "time": {
                "$gte": start,
                "$lt": end
            }
        }).limit(500)
        return cursor
    except ConnectionError  as e:
        print("Connection Error")
        return []


def generate_time_intervals(start1, interval_size, end1):
    """
   :param  (int) interval_size: interval size to break to in milli seconds
   :param (int) start1: start time in milliseconds
   :param (int) end1: end time in milliseconds
   :return: list of time intervals
   """
    start1 = int(start1)
    end1 = int(end1)
    interval_list1 = []
    n = int((end1 - start1) / interval_size)
    print("n: " + str(n))
    counter = start1
    for i in range(n):
        interval_list1.append([counter, counter + interval_size])
        counter += interval_size

    return interval_list1


def get_result_table(data):
    res = {}
    col_name = Config.MONGO_IP_COLUMN_NAME
    for i in data:
        if i[col_name] not in res:
            res[i[col_name]] = 1
        else:
            res[i[col_name]] += 1
    return res


def spawn_threads(mongo_res):
    try:
        start = int(datetime.now().timestamp() * 1000 - float(Config.SLIDING_WINDOW) * 1000)
        end = int(datetime.now().timestamp() * 1000)
        interval_list = generate_time_intervals(start, int(Config.SLIDING_WINDOW_PIECE) * 1000, end)
        data_list1 = []
        for lst in interval_list:
            data = get_data_in_interval(mongo_res, lst[0], lst[1])
            data_list1.append(get_result_table(data))
        # print("Interval list: ", interval_list)
        # print("Data list1: ", data_list1)

        var_thread = Thread(target=variance_method, args=(data_list1,))
        var_thread.daemon = True
        var_thread.setName("Variance Method thread")

        slide_thread = Thread(target=sliding_window, args=(data_list1,))
        slide_thread.daemon = True
        slide_thread.setName("Sliding Window thread")

        var_thread.start()
        slide_thread.start()
        print("Threads started :" + var_thread.getName() + ", " + slide_thread.getName())
    except BaseException as e:
        print("Error in Spawn threads")
        print(e)


def task():
    my_client = pymongo.MongoClient(Config.MONGO_URI)
    my_db = my_client[Config.MONGO_DATABASE]
    mongo_res = my_db[Config.MONGO_LOG_COLLECTION]
    interval_size = Config.SLIDING_WINDOW
    beta = Config.BETA
    omega = Config.OMEGA

    scheduler = BackgroundScheduler()
    job = scheduler.add_job(func=spawn_threads, args=[mongo_res], trigger='interval', seconds=3)
    try:
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        print("Error in task function")
        print(e)



if __name__ == "__main__":
    task()
