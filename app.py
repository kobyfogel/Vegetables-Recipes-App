from os import getenv
import random
import string

from dotenv import load_dotenv
from flask import Flask, render_template, request, url_for
import requests


app = Flask(__name__)
load_dotenv(override=True)
FDC_key = getenv('FDC_KEY')
SPOON_key = getenv('SPOON_KEY')


@app.route("/")
@app.route("/home")
def home():
    vegetable_name = request.args.get("search-vegetable-form")
    ingredients = request.args.get("recipe-search")
    if vegetable_name:
        return vegetable_result(veg=vegetable_name)
    if ingredients:
        return recipe_results(ingredients=ingredients)
    return render_template('index.html', title="Vegetables Nutrition and recipes")


@app.route("/vegetable_result/<string:veg>")
def vegetable_result(veg):
    query = f"{veg}(fresh)(raw)"
    resp = requests.get(
        f'https://api.nal.usda.gov/fdc/v1/foods/search?api_key={FDC_key}&query={query}&datatype=Survey&pagesize=1')
    resp = resp.json()['foods'][0]['foodNutrients']
    ordered_nutritions = {}
    total = 0
    for i in (resp):
        if i['value'] > 0 and not i['nutrientName'].replace(":", "").isdigit() and i['unitName'] != "kJ" and i['unitName'] != "KCAL":
            if i['unitName'] == "UG":
                i['value'] /= 1000000
            elif i['unitName'] == "MG":
                i['value'] /= 1000
            elif 'RAE' in i['nutrientName']:
                i['value'] = 0
            elif "IU" in i['unitName']:
                if 'Vitamin A' in i['nutrientName']:
                    i['value'] = (i['value'] / 1667) / 1000
                if 'Vitamin D' in i['nutrientName']:
                    i['value'] = (i['value'] / 1.3) / 1000
                if 'Vitamin E' in i['nutrientName']:
                    i['value'] = (i['value'] / 1667) / 1000
            total += i['value']
            ordered_nutritions[i['nutrientName']] = i['value']
    for nutrition, value in ordered_nutritions.items():
        ordered_nutritions[nutrition] = value / total * 100
    ordered_nutritions = sorted(ordered_nutritions.items(), key=lambda kv: kv[1], reverse=True)[:15]
    nutritions_list = []
    for nutrition in ordered_nutritions:
        nutritions_list.append(f"{nutrition[0]}: {round(nutrition[1], 5)}")
    ingred = request.args.get("recipe-search")
    if ingred:
        return recipe_results(ingredients=ingred)
    return render_template('vegetable_result.html', title="vegetable compounds", nutritions=nutritions_list, veg=string.capwords(veg))


@app.route("/recipe_result/<string:ingredients>")
def recipe_results(ingredients):
    resp = requests.get(f'https://api.spoonacular.com/recipes/findByIngredients?apiKey={SPOON_key}&ingredients={ingredients}&number=20&limitLicense=false')
    recipes = resp.json()
    valid = False
    while not valid:
        try:
            recipe = random.choice(recipes)
        except IndexError:
            return render_template("recipe_result.html", title="Recipes", ingredients=string.capwords(ingredients), recipe_name="", recipe_pic=url_for('static', filename='/icons/vegetable.svg'), ingredients_list=['Could not find recipe!', 'Please check your ingredients!'], instructions_list=[])
        recipe_id = recipe['id']
        recipe_name = recipe['title']
        recipe_pic = recipe['image']
        resp = requests.get(f'https://api.spoonacular.com/recipes/{recipe_id}/analyzedInstructions?apiKey={SPOON_key}')
        instructions = resp.json()
        try:
            if "steps" in instructions[0]:
                valid = True
        except IndexError:
            pass
    ingredients_list = []
    for i in (recipe['usedIngredients']):
        ingredients_list.append(i['original'])
    for i in (recipe['missedIngredients']):
        ingredients_list.append(i['original'])
    instructions_list = [i['step'] for i in instructions[0]['steps']]
    return render_template("recipe_result.html", title="Recipes", ingredients=string.capwords(ingredients), recipe_name=recipe_name, recipe_pic=recipe_pic, ingredients_list=ingredients_list, instructions_list=instructions_list)


if __name__ == '__main__':
    app.run(threaded=True, port=5000, debug=True)
