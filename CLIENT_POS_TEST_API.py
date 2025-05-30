import requests
import json
import time # For pausing between tests if needed

BASE_URL = "http://127.0.0.1:5000"

def run_test(name, func):
    """Helper function to run and display test results."""
    print(f"\n--- Running Test: {name} ---")
    try:
        func()
        print(f"--- Test Passed: {name} ---")
    except requests.exceptions.HTTPError as e:
        print(f"--- Test Failed: {name} (HTTP Error: {e.response.status_code}) ---")
        if e.response.status_code == 400 or e.response.status_code == 500:
            print(f"Response Body: {e.response.text}")
    except AssertionError as e:
        print(f"--- Test Failed: {name} (Assertion Error: {e}) ---")
    except Exception as e:
        print(f"--- Test Failed: {name} (Unexpected Error: {e}) ---")

def test_get_all_products():
    """Tests GET /products (from index.html route, but can be accessed as API for JSON)."""
    response = requests.get(f"{BASE_URL}/") # Accessing the root route which serves products
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    # For the root route, it returns HTML, so we can't assert on JSON directly.
    # To test product data via API, we'd need a dedicated /api/products endpoint.
    # For now, we'll test the new product via HTML form response or sales_api.
    print("GET /products (HTML) successful.")


def test_add_new_product_success():
    """Tests POST /products (via form submission)."""
    new_product_data = {
        'sku': f'TESTSKU{int(time.time())}', # Unique SKU using timestamp
        'name': 'Test Product A',
        'price': '9.99',
        'stock_quantity': '100'
    }
    response = requests.post(f"{BASE_URL}/products", data=new_product_data)
    # Expect a redirect (302) if success, and then a 200 for the redirected page
    assert response.status_code == 200, f"Expected status 200 after redirect, got {response.status_code}"
    assert 'Product "Test Product A" added successfully!' in response.text, "Success message not found"
    print(f"Added product: {new_product_data['name']} ({new_product_data['sku']})")
    return new_product_data['sku'] # Return SKU for subsequent tests

def test_add_duplicate_product_failure(sku_to_duplicate):
    """Tests POST /products with a duplicate SKU."""
    duplicate_product_data = {
        'sku': sku_to_duplicate,
        'name': 'Duplicate Product',
        'price': '1.00',
        'stock_quantity': '10'
    }
    response = requests.post(f"{BASE_URL}/products", data=duplicate_product_data)
    assert response.status_code == 200, f"Expected status 200 after redirect, got {response.status_code}"
    assert f'Product with SKU "{sku_to_duplicate}" already exists.' in response.text, "Duplicate SKU error message not found"
    print(f"Correctly failed to add duplicate product with SKU: {sku_to_duplicate}")


def test_get_all_sales_api():
    """Tests GET /sales_api."""
    response = requests.get(f"{BASE_URL}/sales_api")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    assert isinstance(response.json(), list), "Expected a list of sales"
    print(f"Retrieved {len(response.json())} sales via API.")


def test_process_sale_success(product_sku):
    """Tests POST /process_sale for a successful transaction."""
    sale_items = [
        {"product_sku": product_sku, "quantity": 1},
        {"product_sku": "SKU002", "quantity": 2} # Assume SKU002 exists and has enough stock
    ]
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{BASE_URL}/process_sale", headers=headers, json=sale_items)
    assert response.status_code == 201, f"Expected status 201, got {response.status_code}"
    assert 'sale_id' in response.json(), "Sale ID not found in success response"
    assert 'total_amount' in response.json(), "Total amount not found in success response"
    print(f"Sale processed successfully. Sale ID: {response.json()['sale_id']}")
    return response.json()['sale_id']

def test_process_sale_insufficient_stock_failure():
    """Tests POST /process_sale for insufficient stock scenario."""
    # Try to sell more than available (assuming SKU001 initial stock is 50, and 1 already sold)
    failing_items = [
        {"product_sku": "SKU001", "quantity": 1000}
    ]
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{BASE_URL}/process_sale", headers=headers, json=failing_items)
    assert response.status_code == 400, f"Expected status 400 for insufficient stock, got {response.status_code}"
    assert "Insufficient stock" in response.json().get('error', ''), "Expected insufficient stock error message"
    print("Correctly failed sale due to insufficient stock.")


def test_get_sale_details_success(sale_id):
    """Tests GET /sale/<id> for a successful retrieval."""
    response = requests.get(f"{BASE_URL}/sale/{sale_id}")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    assert 'items' in response.json(), "Expected sale items in details response"
    assert response.json()['id'] == sale_id, "Returned sale ID mismatch"
    print(f"Retrieved details for sale ID: {sale_id}")

def test_get_sale_details_not_found():
    """Tests GET /sale/<id> for a non-existent sale."""
    response = requests.get(f"{BASE_URL}/sale/999999") # Assuming this ID doesn't exist
    assert response.status_code == 404, f"Expected status 404, got {response.status_code}"
    assert "Sale not found" in response.json().get('error', ''), "Expected 'Sale not found' error message"
    print("Correctly failed to retrieve non-existent sale.")


def test_update_product_success(sku_to_update):
    """Tests PUT /products/<sku> for a successful update."""
    updated_data = {
        "name": "Updated Test Product Name",
        "price": 12.50,
        "stock_quantity": 75
    }
    headers = {"Content-Type": "application/json"}
    response = requests.put(f"{BASE_URL}/products/{sku_to_update}", headers=headers, json=updated_data)
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    assert f"Product '{sku_to_update}' updated successfully." in response.json().get('message', '')
    print(f"Product {sku_to_update} updated successfully.")

    # Verify the update by fetching the product data
    # NOTE: You'd need a GET /products/<sku> API endpoint for this
    # Since we don't have a direct /products/<sku> API in the current app,
    # you'd typically verify via UI or a dedicated GET API endpoint if you built one.
    # For this example, we'll skip direct verification, but mention it.
    print("Verification of PUT update would typically involve a GET /products/<sku> API call.")


def test_update_product_not_found():
    """Tests PUT /products/<sku> for a non-existent product."""
    non_existent_sku = "NONEXISTENTSKU"
    update_data = {
        "name": "Fake Product",
        "price": 1.0,
        "stock_quantity": 10
    }
    headers = {"Content-Type": "application/json"}
    response = requests.put(f"{BASE_URL}/products/{non_existent_sku}", headers=headers, json=update_data)
    assert response.status_code == 404, f"Expected status 404, got {response.status_code}"
    assert f"Product with SKU '{non_existent_sku}' not found." in response.json().get('error', '')
    print(f"Correctly failed to update non-existent product: {non_existent_sku}.")


if __name__ == "__main__":
    print("Starting API Tests...")
    print("Ensure your Flask app is running at http://127.0.0.1:5000 before running tests.")
    time.sleep(2) # Give Flask app a moment to start, if just launched

    # Test sequence
    run_test("GET All Products (HTML view)", test_get_all_products)

    # Add a new product and get its SKU for subsequent tests
    new_sku = None
    try:
        new_sku = run_test("Add New Product Success", test_add_new_product_success)
    except Exception:
        pass # Handle if test_add_new_product_success failed to return SKU

    if new_sku:
        run_test(f"Add Duplicate Product Failure (SKU: {new_sku})", lambda: test_add_duplicate_product_failure(new_sku))
        run_test(f"Update Product Success (SKU: {new_sku})", lambda: test_update_product_success(new_sku))

    run_test("GET All Sales API", test_get_all_sales_api)

    # Process a sale and get its ID for subsequent tests
    sale_id = None
    # We use new_sku if it was successfully added, otherwise use a default SKU (e.g., 'SKU001')
    product_for_sale_test = new_sku if new_sku else 'SKU001'
    try:
        sale_id = run_test(f"Process Sale Success (using {product_for_sale_test})", lambda: test_process_sale_success(product_for_sale_test))
    except Exception:
        pass # Handle if test_process_sale_success failed to return ID

    run_test("Process Sale Insufficient Stock Failure", test_process_sale_insufficient_stock_failure)

    if sale_id:
        run_test(f"GET Sale Details Success (ID: {sale_id})", lambda: test_get_sale_details_success(sale_id))

    run_test("GET Sale Details Not Found", test_get_sale_details_not_found)
    run_test("Update Non-Existent Product Failure", test_update_product_not_found)

    print("\n--- All Tests Completed ---")