import json
import os
import re
import shutil
import traceback
import uuid
from datetime import datetime, timedelta

import fitz
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, session
from whoosh import index as indexx
from whoosh.qparser import QueryParser

DEBUG = True


def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        pass


def clear():
    shutil.rmtree(f"static/images/{user_id}")


app = Flask(__name__)
app.secret_key = "edexcel_finder_anonymouslyanonymous"
scheduler = BackgroundScheduler()
scheduler.start()

SUBJECTS = {
    "Further-Maths": {
        "F1": {"new": {"code": "WFM01", "chapters": []}},
        "F2": {"new": {"code": "WFM02", "chapters": []}},
        "F3": {"new": {"code": "WFM03", "chapters": []}},
    },
    "Pure": {
        "P1": {"new": {"code": "WMA01", "chapters": []}},
        "P2": {"new": {"code": "WMA02", "chapters": []}},
        "P3": {"new": {"code": "WMA03", "chapters": []}},
        "P4": {"new": {"code": "WMA04", "chapters": []}},
    },
    "Mechanics": {
        "M1": {"new": {"code": "WME01", "chapters": []}},
        "M2": {"new": {"code": "WME02", "chapters": []}},
        "M3": {"new": {"code": "WME03", "chapters": []}},
    },
    "Statistics": {
        "S1": {"new": {"code": "WST01", "chapters": []}},
        "S2": {"new": {"code": "WST02", "chapters": []}},
        "S3": {"new": {"code": "WST03", "chapters": []}},
    },
    "Decision": {
        "D1": {
            "new": {"code": "WDM11", "chapters": []},
            "old": {"code": "WDM01", "chapters": []},
        },
    },
    "Chemistry": {
        "U1": {"new": {"code": "WCH11", "chapters": []}},
        "U2": {"new": {"code": "WCH12", "chapters": []}},
        "U3": {"new": {"code": "WCH13", "chapters": []}},
        "U4": {"new": {"code": "WCH14", "chapters": []}},
        "U5": {"new": {"code": "WCH15", "chapters": []}},
        "U6": {"new": {"code": "WCH16", "chapters": []}},
    },
    "Physics": {
        "U1": {"new": {"code": "WPH11", "chapters": []}},
        "U2": {"new": {"code": "WPH12", "chapters": []}},
        "U3": {"new": {"code": "WPH13", "chapters": []}},
        "U4": {"new": {"code": "WPH14", "chapters": []}},
        "U5": {"new": {"code": "WPH15", "chapters": []}},
        "U6": {"new": {"code": "WPH16", "chapters": []}},
    },
    "Biology": {
        "U1": {"new": {"code": "WBI11", "chapters": []}},
        "U2": {"new": {"code": "WBI12", "chapters": []}},
        "U3": {"new": {"code": "WBI13", "chapters": []}},
        "U4": {"new": {"code": "WBI14", "chapters": []}},
        "U5": {"new": {"code": "WBI15", "chapters": []}},
        "U6": {"new": {"code": "WBI16", "chapters": []}},
    },
}


@app.route("/", methods=["GET", "POST"])
def index():
    global user_id
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    user_id = session["user_id"]
    # print(f"user ID: {user_id}")
    return render_template("index.html", subjects=SUBJECTS)


@app.route("/results", methods=["GET", "POST"])
def results():
    global user_id
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    user_id = session["user_id"]
    send = []
    subject = request.args.get("subject")
    unit_code = request.args.get("unit-code")
    if unit_code and "-" in unit_code:
        unit_code, specification = unit_code.split("-")
    if subject != "Physics" and subject != "Chemistry" and subject != "Biology":
        subject = "Mathematics"
    else:
        subject = "None"
    target = request.args.get("search").lower()
    folder = []
    if specification == "both":
        old = f"Old {subject}"
        folder.append(["Old Specification", old])
        new = f"{subject} (2018)"
        folder.append(["New Specification", new])
    elif specification == "new":
        todo = f"{subject} (2018)"
    else:
        todo = f"Old {subject}"
    total = 0
    old_count = 0
    new_count = 0
    ensure_directory(f"static/images/{user_id}")
    if folder:
        for one in folder:
            ix = indexx.open_dir(f"static/Index/{one[1]}/{unit_code}")
            qp = QueryParser("content", schema=ix.schema)
            query = qp.parse(target)
            with ix.searcher() as searcher:
                results = searcher.search(query, limit=None)
                for result in results:
                    if result["year"] != "Sample Assessment":
                        response = requests.get(result["qp_link"])
                        if response.status_code != 200:
                            continue
                        else:
                            pdf = open("static/QP.pdf", "wb")
                            pdf.write(response.content)
                            page = result["page"]
                            try:
                                pdf = fitz.open("static/QP.pdf")
                                # print(f"{result['year']} {result['qp_link']}#page={page}")
                                Page = pdf.load_page(page)
                                pix = Page.get_pixmap(dpi=160)
                                ensure_directory(f"static/images/{user_id}/{one[0]}")
                                pix.save(
                                    f"static/images/{user_id}/{one[0]}/{result['year']} pg{page}.png"
                                )
                                send.append(
                                    [
                                        result["year"],
                                        page + 1,
                                        f"static/images/{user_id}/{one[0]}/{result['year']} pg{page}.png",
                                        result["qp_link"],
                                        result["ms_link"],
                                    ]
                                )
                            except:
                                webhook_url = ""

                                data = {
                                    "content": f"# Data Omitted \n > {result['year']} {subject} {subject} \n - Question Paper: {result['qp_link']}#page={result['page']} \n - Search Term: {target}"
                                }

                                response = requests.post(webhook_url, json=data)

                                if response.status_code == 204:
                                    print("Message sent successfully!")
                                else:
                                    print(
                                        f"Failed to send message: {response.status_code}"
                                    )
                                send.append(
                                    [
                                        result["year"],
                                        page + 1,
                                        "static/404.png",
                                        result["qp_link"],
                                        result["ms_link"],
                                    ]
                                )
                    else:
                        page = result["page"]
                        pdf = fitz.open(f"{result['qp_link']}")
                        Page = pdf.load_page(page)
                        pix = Page.get_pixmap(dpi=160)
                        ensure_directory(f"static/images/{user_id}/{one[0]}")
                        pix.save(
                            f"static/images/{user_id}/{one[0]}/{result['year']} pg{page}.png"
                        )
                        send.append(
                            [
                                result["year"],
                                page + 1,
                                f"static/images/{user_id}/{one[0]}/{result['year']} pg{page}.png",
                                result["qp_link"],
                                result["ms_link"],
                            ]
                        )
            total = total + len(results)
            if one[1] == old:
                old_count = len(results)
            else:
                new_count = len(results)

        hits = f"{total} [Old: {old_count}, New: {new_count}]"
        run_time = datetime.now() + timedelta(seconds=400)
        scheduler.add_job(clear, "date", run_date=run_time)
        send.sort(
            key=lambda x: datetime.strptime("June 2019", "%B %Y")
            if x[0] == "Sample Assessment"
            else datetime.strptime(re.sub(r"^Unused ", "", x[0]), "%B %Y")
            if x[0].startswith("Unused ")
            else datetime.strptime(x[0], "%B %Y")
        )
        return render_template("results.html", results=send, hits=hits)
    else:
        print(f"static/Index/{todo}/{unit_code}")
        ix = indexx.open_dir(f"static/Index/{todo}/{unit_code}")
        qp = QueryParser("content", schema=ix.schema)
        query = qp.parse(target)
        with ix.searcher() as searcher:
            results = searcher.search(query, limit=None)
            for result in results:
                if result["year"] != "Sample Assessment":
                    response = requests.get(result["qp_link"])
                    if response.status_code != 200:
                        continue
                    else:
                        pdf = open("static/QP.pdf", "wb")
                        pdf.write(response.content)
                        page = result["page"]
                        try:
                            pdf = fitz.open("static/QP.pdf")
                            # print(f"{result['year']} {result['qp_link']}#page={page}")
                            Page = pdf.load_page(page)
                            pix = Page.get_pixmap(dpi=160)
                            ensure_directory(f"static/images/{user_id}/{todo}")
                            pix.save(
                                f"static/images/{user_id}/{todo}/{result['year']} pg{page}.png"
                            )
                            send.append(
                                [
                                    result["year"],
                                    page + 1,
                                    f"static/images/{user_id}/{todo}/{result['year']} pg{page}.png",
                                    result["qp_link"],
                                    result["ms_link"],
                                ]
                            )
                        except:
                            webhook_url = ""

                            data = {
                                "content": f"# Data Omitted \n > {result['year']} {subject} {subject} \n - Question Paper: {result['qp_link']}#page={result['page'] + 1} \n - Search Term: {target}"
                            }

                            response = requests.post(webhook_url, json=data)

                            if response.status_code == 204:
                                print("Message sent successfully!")
                            else:
                                print(f"Failed to send message: {response.status_code}")
                            send.append(
                                [
                                    result["year"],
                                    page + 1,
                                    "static/404.png",
                                    result["qp_link"],
                                    result["ms_link"],
                                ]
                            )
                else:
                    page = result["page"]
                    pdf = fitz.open(f"{result['qp_link']}")
                    Page = pdf.load_page(page)
                    pix = Page.get_pixmap(dpi=160)
                    ensure_directory(f"static/images/{user_id}/{todo}")
                    pix.save(
                        f"static/images/{user_id}/{todo}/{result['year']} pg{page}.png"
                    )
                    send.append(
                        [
                            result["year"],
                            page + 1,
                            f"static/images/{user_id}/{todo}/{result['year']} pg{page}.png",
                            result["qp_link"],
                            result["ms_link"],
                        ]
                    )
        total = len(results)
        hits = total
        run_time = datetime.now() + timedelta(seconds=400)
        scheduler.add_job(clear, "date", run_date=run_time)
        send.sort(
            key=lambda x: datetime.strptime("June 2019", "%B %Y")
            if x[0] == "Sample Assessment"
            else datetime.strptime(re.sub(r"^Unused ", "", x[0]), "%B %Y")
            if x[0].startswith("Unused ")
            else datetime.strptime(x[0], "%B %Y")
        )
        return render_template("results.html", results=send, hits=hits)


@app.route("/SixMark", methods=["GET", "POST"])
def SixMark():
    global user_id
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    user_id = session["user_id"]
    # print(f"user ID: {user_id}")
    return render_template("SixMark.html")


@app.route("/SixMarkresults", methods=["GET", "POST"])
def SixMarkresults():
    send = []
    subject = request.args.get("subject")
    unit = request.args.get("unit")
    specification = request.args.get("specification")
    folder = []
    if specification == "both":
        old = f"Old {subject}"
        folder.append(["Old Specification", old])
        new = f"{subject} (2018)"
        folder.append(["New Specification", new])
    elif specification == "new":
        todo = f"{subject} (2018)"
    else:
        todo = f"Old {subject}"
    total = 0
    old_count = 0
    new_count = 0
    if folder:
        for one in folder:
            for file in os.listdir(f"static/SixMark/Data/{one[1]}/{unit}"):
                data = open(
                    f"static/SixMark/Data/{one[1]}/{unit}/{file}", "r", encoding="utf-8"
                )
                data = json.load(data)
                for row in data:
                    send.append(
                        [
                            row["Title"],
                            row["Page"],
                            row["Image_Link"],
                            row["QP_Link"],
                            row["MS_Link"],
                        ]
                    )
                    total = total + 1
                    if one[1] == old:
                        old_count = old_count + 1
                    else:
                        new_count = new_count + 1
        hits = f"{total} [Old: {old_count}, New: {new_count}]"
        send.sort(
            key=lambda x: datetime.strptime("June 2019", "%B %Y")
            if x[0] == "Sample Assessment"
            else datetime.strptime(re.sub(r"^Unused ", "", x[0]), "%B %Y")
            if x[0].startswith("Unused ")
            else datetime.strptime(re.sub(r"^June 2013 ", "June 2013", x[0]), "%B %Y")
            if x[0].startswith("June 2013 ")
            else datetime.strptime("June 2014", "%B %Y")
            if x[0].startswith("1R June 2014")
            else datetime.strptime(x[0], "%B %Y")
        )
    else:
        for file in os.listdir(f"static/SixMark/Data/{todo}/{unit}"):
            data = open(
                f"static/SixMark/Data/{todo}/{unit}/{file}", "r", encoding="utf-8"
            )
            data = json.load(data)
            for row in data:
                send.append(
                    [
                        row["Title"],
                        row["Page"],
                        row["Image_Link"],
                        row["QP_Link"],
                        row["MS_Link"],
                    ]
                )
                total = total + 1
        hits = total
        send.sort(
            key=lambda x: datetime.strptime("June 2019", "%B %Y")
            if x[0] == "Sample Assessment"
            else datetime.strptime(re.sub(r"^Unused ", "", x[0]), "%B %Y")
            if x[0].startswith("Unused ")
            else datetime.strptime(re.sub(r"^June 2013 ", "June 2013", x[0]), "%B %Y")
            if x[0].startswith("June 2013 ")
            else datetime.strptime("June 2014", "%B %Y")
            if x[0].startswith("1R June 2014")
            else datetime.strptime(x[0], "%B %Y")
        )
    return render_template("resultsSixMark.html", results=send, hits=hits)


@app.route("/SixMarkSearch", methods=["GET", "POST"])
def SixMarkSearch():
    global user_id
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    user_id = session["user_id"]
    # print(f"user ID: {user_id}")
    return render_template("SixMarkSearch.html")


@app.route("/SixMarkSearchresults", methods=["GET", "POST"])
def SixMarkSearchresults():
    send = []
    subject = request.args.get("subject")
    unit = request.args.get("unit")
    specification = request.args.get("specification")
    target = request.args.get("search").lower()
    folder = []
    if specification == "both":
        old = f"Old {subject}"
        folder.append(["Old Specification", old])
        new = f"{subject} (2018)"
        folder.append(["New Specification", new])
    elif specification == "new":
        todo = f"{subject} (2018)"
    else:
        todo = f"Old {subject}"
    total = 0
    old_count = 0
    new_count = 0
    if folder:
        for one in folder:
            ix = indexx.open_dir(f"static/SixMark/Index/{one[1]}/{unit}")
            qp = QueryParser("content", schema=ix.schema)
            query = qp.parse(target)
            with ix.searcher() as searcher:
                results = searcher.search(query, limit=None)
                for result in results:
                    send.append(
                        [
                            result["year"],
                            result["page"],
                            result["image_link"],
                            result["qp_link"],
                            result["ms_link"],
                        ]
                    )
            total = total + len(results)
            if one[1] == old:
                old_count = len(results)
            else:
                new_count = len(results)
        hits = f"{total} [Old: {old_count}, New: {new_count}]"
        send.sort(
            key=lambda x: datetime.strptime("June 2019", "%B %Y")
            if x[0] == "Sample Assessment"
            else datetime.strptime(re.sub(r"^Unused ", "", x[0]), "%B %Y")
            if x[0].startswith("Unused ")
            else datetime.strptime(re.sub(r"^June 2013 ", "June 2013", x[0]), "%B %Y")
            if x[0].startswith("June 2013 ")
            else datetime.strptime("June 2014", "%B %Y")
            if x[0].startswith("1R June 2014")
            else datetime.strptime(x[0], "%B %Y")
        )
        return render_template("resultsSixMarkSearch.html", results=send, hits=hits)
    else:
        ix = indexx.open_dir(f"static/SixMark/Index/{todo}/{unit}")
        qp = QueryParser("content", schema=ix.schema)
        query = qp.parse(target)
        with ix.searcher() as searcher:
            results = searcher.search(query, limit=None)
            for result in results:
                send.append(
                    [
                        result["year"],
                        result["page"],
                        result["image_link"],
                        result["qp_link"],
                        result["ms_link"],
                    ]
                )
        total = len(results)
        hits = total
        send.sort(
            key=lambda x: datetime.strptime("June 2019", "%B %Y")
            if x[0] == "Sample Assessment"
            else datetime.strptime(re.sub(r"^Unused ", "", x[0]), "%B %Y")
            if x[0].startswith("Unused ")
            else datetime.strptime(re.sub(r"^June 2013 ", "June 2013", x[0]), "%B %Y")
            if x[0].startswith("June 2013 ")
            else datetime.strptime("June 2014", "%B %Y")
            if x[0].startswith("1R June 2014")
            else datetime.strptime(x[0], "%B %Y")
        )
        return render_template("resultsSixMarkSearch.html", results=send, hits=hits)


@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", error=str(traceback.format_exc())), 500


if __name__ == "__main__":
    app.run(debug=DEBUG)
