import sqlite3
import threading
import time
from queue import Queue
import requests
from lxml import html
import sys


def check_plate(state, plate):
    url = f'https://findbyplate.com/US/{state}/{plate}/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    tries = 3

    while tries > 0:
        try:
            response = requests.get(url, headers=headers)
            if response.ok:
                page = html.fromstring(response.content)
                if len(page.xpath('//i[@class="fa-spinner"]')) < 2:
                    results = page.xpath('//h2[@class="vehicle-modal"]/text()')
                    if results:
                        return results[0].strip()
                    else:
                        return "NONE"
                else:
                    return "NONE"
            else:
                print(f'\nResponse error {response.status_code} for {plate}')
                tries -= 1
                time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            print(f'\nConnection error for {plate}: {e}')
            tries -= 1
            time.sleep(1)


def worker(state, q: Queue, db_filename, times) -> None:
    conn = sqlite3.connect(db_filename)
    while True:
        start_time = time.monotonic()
        plate = q.get()
        if plate is None:
            break
        cursor = conn.cursor()
        model = check_plate(state, plate)
        cursor.execute("INSERT INTO plates VALUES (?, ?)", (plate, model))
        conn.commit()
        cursor.close()
        q.task_done()
        end_time = time.monotonic()
        times.append(end_time - start_time)
    conn.close()


def main() -> None:
    num_threads = 128
    state = sys.argv[1]

    chars = [f"{i}" for i in range(10)] + [chr(i)
                                           for i in range(ord("A"), ord("Z") + 1)]

    conn = sqlite3.connect('plates.db')
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS plates (plate TEXT, model TEXT)")
    conn.commit()

    q = Queue()

    for a in chars:
        for b in chars:
            for c in chars:
                plate = f"C42{a}{b}{c}"
                q.put(plate)

    qsize = q.qsize()
    threads = []
    times = []

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(
            state, q, 'plates.db', times))
        t.start()
        threads.append(t)

    while not q.empty():
        remaining = q.qsize()
        completed = qsize - remaining
        if completed > 0 and len(times) > 0:
            avg_time = sum(times) / len(times)
            remaining_time = (remaining / num_threads) * avg_time
            progress = f" Progress: {completed}/{qsize}, " \
                       f"Estimated Time: {remaining_time:.2f}s remaining"
            print(progress, end='\r')
        time.sleep(0.5)

    q.join()
    for i in range(num_threads):
        q.put(None)
    for t in threads:
        t.join()

    cur.execute("SELECT plate, model FROM plates WHERE model LIKE '%HYUNDAI%'")
    results = cur.fetchall()

    print("\nResults:")
    for row in results:
        print("  ", row)

    conn.close()


if __name__ == "__main__":
    main()
