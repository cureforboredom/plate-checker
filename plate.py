import sqlite3
import threading
import time
from queue import Queue
import requests
from lxml import html


def check_plate(plate):
    url = f'https://findbyplate.com/US/GA/{plate}/'
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
                print(f'Response error {response.status_code} for {plate}')
                tries -= 1
                time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            print(f'Connection error for {plate}: {e}')
            tries -= 1
            time.sleep(1)


def worker(q: Queue, db_filename, times) -> None:
    conn = sqlite3.connect(db_filename)
    while True:
        start_time = time.monotonic()
        plate = q.get()
        if plate is None:
            break
        cursor = conn.cursor()
        model = check_plate(plate)
        cursor.execute("INSERT INTO plates VALUES (?, ?)", (plate, model))
        conn.commit()
        cursor.close()
        q.task_done()
        end_time = time.monotonic()
        times.append(end_time - start_time)
    conn.close()


def main() -> None:
    num_threads = 128

    conn = sqlite3.connect('plates.db')
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS plates (plate TEXT, model TEXT)")
    conn.commit()

    q = Queue()

    for n in ["%04d" % i for i in range(0, 9999)]:
        plate = f"TEF{n}"
        q.put(plate)

    qsize = q.qsize()
    threads = []
    times = []

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(q, 'plates.db', times))
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

    cur.execute("SELECT plate, model FROM plates WHERE model LIKE '%NISSAN%'")
    results = cur.fetchall()

    print("\nResults:")
    for row in results:
        print("  ", row)

    conn.close()


if __name__ == "__main__":
    main()
