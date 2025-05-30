import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def get_all_sales():
    """Fetches all sales from the API."""
    response = requests.get(f"{BASE_URL}/sales_api")
    response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
    print("\n--- All Sales ---")
    print(json.dumps(response.json(), indent=2))

def get_sale_details(sale_id):
    """Fetches details for a specific sale."""
    response = requests.get(f"{BASE_URL}/sale/{sale_id}")
    response.raise_for_status()
    print(f"\n--- Sale Details for ID {sale_id} ---")
    print(json.dumps(response.json(), indent=2))

def process_new_sale(items):
    """Processes a new sale with the given items."""
    print("\n--- Processing New Sale ---")
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{BASE_URL}/process_sale", headers=headers, json=items)

    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Error: Could not decode JSON from response. Status: {response.status_code}, Response: {response.text}")
        return

    if response.status_code == 201:
        print(f"Success! Sale ID: {response_json.get('sale_id')}, Total: ${response_json.get('total_amount'):.2f}")
    else:
        print(f"Error ({response.status_code}): {response_json.get('error', 'Unknown error')}")
    print(json.dumps(response_json, indent=2))
    response.raise_for_status() # Raise exception for non-2xx status after printing


if __name__ == "__main__":
    # Ensure your Flask app is running before executing this script

    # Test GET requests
    get_all_sales()

    # Process a new sale
    # This example requires SKU001 and SKU003 to be in stock
    sample_items = [
        {"product_sku": "SKU001", "quantity": 1},
        {"product_sku": "SKU003", "quantity": 2}
    ]
    process_new_sale(sample_items)

    # Process a sale that should fail (e.g., insufficient stock)
    # Adjust quantity to be higher than available stock for SKU002
    failing_items = [
        {"product_sku": "SKU002", "quantity": 500} # Assuming stock is less than 500
    ]
    try:
        process_new_sale(failing_items)
    except requests.exceptions.HTTPError:
        print("Expected HTTPError for failing sale.")

    # Get details of the last successful sale (you'll need to know its ID, or fetch all sales again)
    # For simplicity, let's assume the previous sale ID was 3. You can modify this.
    get_sale_details(3)
