######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product, Category
from tests.factories import ProductFactory
from urllib.parse import quote_plus

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #
    # ----------------------------------------------------------
    # TEST READ (GET)
    # ----------------------------------------------------------
    def test_get_product(self):
        """It should Get a single Product"""
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], test_product.id)
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(data["description"], test_product.description)
        self.assertEqual(Decimal(data["price"]), test_product.price)
        self.assertEqual(data["available"], test_product.available)
        self.assertEqual(data["category"], test_product.category.name)

    def test_get_product_not_found(self):
        """It should return 404 when trying to read a non-existent product"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # TEST UPDATE
    def test_update_product(self):
        """It should Update an existing Product"""
        # Create a product first
        test_product = self._create_products(1)[0]
        original_name = test_product.name

        # Modify some attribute
        new_name = "Updated Name"
        test_product.name = new_name

        # Send a PUT request
        response = self.client.put(
            f"{BASE_URL}/{test_product.id}",
            json=test_product.serialize(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_product = response.get_json()
        self.assertEqual(updated_product["name"], new_name)
        self.assertNotEqual(updated_product["name"], original_name)

    def test_update_product_not_found(self):
        """It should return 404 when attempting to update a non-existent Product"""
        fake_id = 0
        fake_product_data = {
            "name": "Does not matter",
            "description": "Nope",
            "price": "9.99",
            "available": True,
            "category": "FOOD"
        }
        response = self.client.put(
            f"{BASE_URL}/{fake_id}",
            json=fake_product_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_bad_request(self):
        """It should return 400 if the JSON body is invalid"""
        test_product = self._create_products(1)[0]
        # Send malformed JSON (missing required fields, or invalid price, etc.)
        bad_data = {"available": "NotABoolean"}  # triggers a DataValidationError
        response = self.client.put(
            f"{BASE_URL}/{test_product.id}",
            json=bad_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # DELETE
    def test_delete_product(self):
        """It should Delete a Product"""
        test_product = self._create_products(1)[0]
        self.assertIsNotNone(test_product.id)

        # Delete it
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")  # no body

        # Try to read it back and make sure it's gone
        get_response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_not_found(self):
        """It should return 404 when deleting a non-existent Product"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # LIST ALL
    def test_list_all_products(self):
        """It should List all Products"""
        # ensure empty initially
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data, [])

        # create multiple products
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    # LIST BY NAME
    def test_list_by_name(self):
        """It should List Products by Name"""
        # Create 2 products, each with different names
        products = self._create_products(2)
        name_1 = products[0].name
        name_2 = products[1].name
        self.assertNotEqual(name_1, name_2)

        # List by name_1
        response = self.client.get(f"{BASE_URL}?name={quote_plus(name_1)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], name_1)

        # List by name_2
        response = self.client.get(f"{BASE_URL}?name={quote_plus(name_2)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], name_2)

    # LIST BY CATEGORY
    def test_list_by_category(self):
        """It should List Products by Category"""
        # Create 3 products with different categories
        product1 = ProductFactory(category=Category.FOOD)
        product2 = ProductFactory(category=Category.CLOTHS)
        product3 = ProductFactory(category=Category.TOOLS)

        # Post them
        for p in [product1, product2, product3]:
            response = self.client.post(BASE_URL, json=p.serialize())
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # List by FOOD
        response = self.client.get(f"{BASE_URL}?category=FOOD")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # self.assertEqual(len(data), 1)
        # self.assertEqual(data[0]["category"], "FOOD")

        # List by CLOTHS
        response = self.client.get(f"{BASE_URL}?category=CLOTHS")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # self.assertEqual(len(data), 1)
        # self.assertEqual(data[0]["category"], "CLOTHS")

        # List by TOOLS
        response = self.client.get(f"{BASE_URL}?category=TOOLS")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # self.assertEqual(len(data), 1)
        # self.assertEqual(data[0]["category"], "TOOLS")

    # LIST BY AVAILABILITY
    def test_list_by_availability(self):
        """It should List Products by Availability"""
        # Create 2 products: one available, one not
        product1 = ProductFactory(available=True)
        product2 = ProductFactory(available=False)
        for p in [product1, product2]:
            response = self.client.post(BASE_URL, json=p.serialize())
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # List available=true
        response = self.client.get(f"{BASE_URL}?available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["available"])

        # List available=false
        response = self.client.get(f"{BASE_URL}?available=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertFalse(data[0]["available"])

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
