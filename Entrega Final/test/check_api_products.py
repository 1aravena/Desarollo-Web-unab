import asyncio
import httpx
import json

async def check_products():
    async with httpx.AsyncClient() as client:
        # Assuming the server is running on localhost:8000
        response = await client.get('http://localhost:8000/api/v1/productos?solo_disponibles=false&solo_activos=false')
        if response.status_code == 200:
            products = response.json()
            print(f"Total products: {len(products)}")
            if products:
                print("First product sample:")
                print(json.dumps(products[0], indent=2))
            else:
                print("No products found.")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(check_products())
