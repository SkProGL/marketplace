import requests

from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def ai_generate(request):
    text = request.query_params.get("q")

    if not text:
        return Response({"error": "Missing ?q= parameter"}, status=400)

    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text,
                "langpair": "en|fr"
            },
            timeout=5
        )

        r.raise_for_status()
        return Response(r.json())

    except requests.RequestException as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def meal_search(request):
    query = request.query_params.get("q", "chicken")

    try:
        r = requests.get(
            "https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": query},
            timeout=5
        )
        r.raise_for_status()
        data = r.json()

        meals = data.get("meals")
        if not meals:
            return Response({"results": []})

        # 🔧 Clean response (important)
        results = []
        for meal in meals:
            results.append({
                "id": meal.get("idMeal"),
                "name": meal.get("strMeal"),
                "category": meal.get("strCategory"),
                "area": meal.get("strArea"),
                "instructions": meal.get("strInstructions"),
                "image": meal.get("strMealThumb"),
            })

        return Response({"results": results})

    except requests.RequestException as e:
        return Response({"error": str(e)}, status=500)
