from flask import Flask, render_template, url_for, flash, redirect, request
import pandas as pd
import os

app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, "new_restaurant.csv.xlsx")

lko_rest = pd.read_excel(file_path)

# ---------- NEW FEATURE : FOOD RECOMMENDATION ----------
def recommend_food(cuisine):
    recommendations = {
        "Biryani": ["Chicken Biryani", "Chicken 65", "Mutton Biryani"],
        "Andhra": ["Andhra Meals", "Gongura Chicken", "Pulihora"],
        "South Indian": ["Dosa", "Idli", "Vada"],
        "Indian": ["Butter Chicken", "Paneer Curry", "Naan"],
        "Multi-cuisine": ["Pizza", "Burger", "Pasta"]
    }
    return recommendations.get(cuisine, ["Chef Special"])
# ------------------------------------------------------


def fav(lko_rest1):
    lko_rest1 = lko_rest1.reset_index()

    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    count1 = CountVectorizer(stop_words='english')
    count_matrix = count1.fit_transform(
        lko_rest1['highlights'].astype(str)
    )

    cosine_sim2 = cosine_similarity(count_matrix, count_matrix)
    sim = list(enumerate(cosine_sim2[0]))
    sim = sorted(sim, key=lambda x: x[1], reverse=True)
    sim = sim[1:11]

    indi = [i[0] for i in sim]

    final = lko_rest1.copy().iloc[indi[0]]
    final = pd.DataFrame(final)
    final = final.T

    for i in range(1, len(indi)):
        final1 = lko_rest1.copy().iloc[indi[i]]
        final1 = pd.DataFrame(final1)
        final1 = final1.T
        final = pd.concat([final, final1])

    return final


def rest_rec(cost, people=2, min_cost=0, cuisine=[], Locality=[], fav_rest="", lko_rest=lko_rest):
    cost = cost + 200
    x = cost / people
    y = min_cost / people

    lko_rest1 = lko_rest.copy().loc[
        lko_rest['locality'] == Locality[0]
    ]

    for i in range(1, len(Locality)):
        lko_rest2 = lko_rest.copy().loc[
            lko_rest['locality'] == Locality[i]
        ]

        lko_rest1 = pd.concat([lko_rest1, lko_rest2])

        lko_rest1.drop_duplicates(
            subset='name',
            keep='last',
            inplace=True
        )

    lko_rest_locale = lko_rest1.copy()

    lko_rest_locale = lko_rest_locale.loc[
        lko_rest_locale['average_cost_for_one'] <= x
    ]

    lko_rest_locale = lko_rest_locale.loc[
        lko_rest_locale['average_cost_for_one'] >= y
    ]

    lko_rest_locale['Start'] = lko_rest_locale[
        'cuisines'
    ].astype(str).str.find(cuisine[0])

    lko_rest_cui = lko_rest_locale.copy().loc[
        lko_rest_locale['Start'] >= 0
    ]

    for i in range(1, len(cuisine)):
        lko_rest_locale['Start'] = lko_rest_locale[
            'cuisines'
        ].astype(str).str.find(cuisine[i])

        lko_rest_cu = lko_rest_locale.copy().loc[
            lko_rest_locale['Start'] >= 0
        ]

        lko_rest_cui = pd.concat([lko_rest_cui, lko_rest_cu])

        lko_rest_cui.drop_duplicates(
            subset='name',
            keep='last',
            inplace=True
        )

    if fav_rest != "":
        favr = lko_rest.loc[
            lko_rest['name'] == fav_rest
        ].drop_duplicates()

        favr = pd.DataFrame(favr)
        lko_rest3 = pd.concat([favr, lko_rest_cui])
        lko_rest3.drop('Start', axis=1, inplace=True)
        rest_selected = fav(lko_rest3)

    else:
        lko_rest_cui = lko_rest_cui.sort_values(
            'scope',
            ascending=False
        )
        rest_selected = lko_rest_cui.head(10)

    return rest_selected



def calc(max_Price, people, min_Price, cuisine, locality):
    rest_sugg = rest_rec(
        max_Price,
        people,
        min_Price,
        [cuisine],
        [locality]
    )

    if rest_sugg.empty:
        return []

    cols = [
        "name",
        "address",
        "locality",
        "timings",
        "aggregate_rating",
        "cuisines",
    ]
    if "google_maps_link" in rest_sugg.columns:
        cols.append("google_maps_link")

    rest_list1 = rest_sugg[cols].copy()

    if "google_maps_link" in rest_list1.columns:
        rest_list1["url"] = rest_list1["google_maps_link"]
        rest_list1.drop(columns=["google_maps_link"], inplace=True)
    else:
        rest_list1["url"] = (
            "https://www.google.com/maps/search/?api=1&query="
            + rest_list1["name"].astype(str)
            + ","
            + rest_list1["locality"].astype(str)
        )

    recommended = ", ".join(recommend_food(cuisine))
    rest_list1["recommended_food"] = recommended

    return rest_list1.to_dict(orient="records")

@app.route("/")
@app.route("/home")
def home():

    # Get all cuisines
    cuisines = []

    for item in lko_rest["cuisines"].dropna():

        for c in str(item).split(","):
            c = c.strip()

            if c not in cuisines:
                cuisines.append(c)

    cuisines = sorted(cuisines)

    # Get all localities
    localities = (
        lko_rest["locality"]
        .dropna()
        .astype(str)
        .str.strip()
        .sort_values()
        .unique()
        .tolist()
    )

    return render_template(
        "home.html",
        cuisines=cuisines,
        localities=localities
    )



@app.route("/search", methods=["POST"])
def search():

    people = int(request.form.get("people"))

    min_Price = int(request.form.get("min_Price"))

    max_Price = int(request.form.get("max_Price"))

    cuisine = request.form.get("cuisine")

    locality = request.form.get("locality")

    restaurants = calc(
        max_Price,
        people,
        min_Price,
        cuisine,
        locality
    )

    return render_template(
        "search.html",
        restaurants=restaurants
    )

if __name__ == '__main__':
    app.run(debug=True)
