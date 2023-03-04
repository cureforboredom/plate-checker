from bs4 import BeautifulSoup as soup
from urllib.request import Request, urlopen


def check_plate(plate):
    url = 'https://findbyplate.com/US/GA/' + plate + '/'
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    webpage = urlopen(req).read()
    page_soup = soup(webpage, "html.parser")
    if len(page_soup.findAll("i", "fa-spinner")) < 2:  # check if plate was found
        return page_soup.findAll("h2", "vehicle-modal")[0].contents[0]
    else:
        return "NONE"


def main():
    # used for testing purposes
    # plate = "TEF0567"

    for n in ["%04d" % i for i in range(0, 9999)]:
        plate = "TEF" + n

        print(plate)

        model = check_plate(plate)

        if model.lower() != "none":
            print("model: " + model.upper())
        if "NISSAN" in model.upper():
            print("Success!")
            break


main()
