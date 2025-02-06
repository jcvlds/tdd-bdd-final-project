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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    #
    # ADD YOUR TEST CASES HERE
    #

    def test_read_a_product(self):
        """It should Read a product from the database"""
        # Create a product in the database
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)

        # Read (find) the product
        found_product = Product.find(product.id)
        self.assertIsNotNone(found_product)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(found_product.price, product.price)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)

    def test_update_a_product(self):
        """It should Update a product in the database"""
        product = ProductFactory(name="Old Name")
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)

        # Update the product
        product.name = "New Name"
        product.update()

        # Fetch it back
        updated_product = Product.find(product.id)
        self.assertIsNotNone(updated_product)
        self.assertEqual(updated_product.name, "New Name")

    def test_delete_a_product(self):
        """It should Delete a product from the database"""
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertEqual(len(Product.all()), 1)

        # Delete the product
        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should List all products in the database"""
        self.assertEqual(Product.all(), [])
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        # Now there should be 5 products in the database
        products = Product.all()
        self.assertEqual(len(products), 5)

    def test_find_by_name(self):
        """It should Find a Product by its name"""
        product = ProductFactory(name="Fuzzy Slippers")
        product.id = None
        product.create()

        product2 = ProductFactory(name="Funky Hat")
        product2.id = None
        product2.create()

        # Search for the first product by name
        found = Product.find_by_name("Fuzzy Slippers")
        self.assertEqual(found.count(), 1)
        self.assertEqual(found.first().id, product.id)
        self.assertEqual(found.first().name, "Fuzzy Slippers")

    def test_find_by_category(self):
        """It should Find Products by Category"""
        product = ProductFactory(category=Category.FOOD)
        product.id = None
        product.create()

        product2 = ProductFactory(category=Category.CLOTHS)
        product2.id = None
        product2.create()

        # Search for products by Category.FOOD
        found = Product.find_by_category(Category.FOOD)
        self.assertEqual(found.count(), 1)
        self.assertEqual(found.first().id, product.id)
        self.assertEqual(found.first().category, Category.FOOD)

    def test_find_by_availability(self):
        """It should Find Products by Availability"""
        product = ProductFactory(available=True)
        product.id = None
        product.create()

        product2 = ProductFactory(available=False)
        product2.id = None
        product2.create()

        # Search for products that are available
        available_products = Product.find_by_availability(True)
        self.assertEqual(available_products.count(), 1)
        self.assertEqual(available_products.first().id, product.id)

        # Search for products that are unavailable
        unavailable_products = Product.find_by_availability(False)
        self.assertEqual(unavailable_products.count(), 1)
        self.assertEqual(unavailable_products.first().id, product2.id)

    def test_update_no_id(self):
        """It should not Update a product without an ID and raise DataValidationError"""
        product = ProductFactory()
        product.id = None  # Ensure the product has no ID
        with self.assertRaises(Exception) as context:
            product.update()
        self.assertIn("empty ID field", str(context.exception))

    def test_deserialize_missing_name(self):
        """It should raise DataValidationError when 'name' is missing"""
        product = Product()
        data = {
            # "name": "Missing on purpose",
            "description": "Test description",
            "price": "10.00",
            "available": True,
            "category": "FOOD"
        }
        with self.assertRaises(Exception) as context:
            product.deserialize(data)
        self.assertIn("missing name", str(context.exception).lower())

    def test_deserialize_non_boolean_available(self):
        """It should raise DataValidationError if 'available' is not boolean"""
        product = Product()
        data = {
            "name": "Test Product",
            "description": "Test description",
            "price": "10.00",
            "available": "Yes",  # Not a boolean
            "category": "FOOD"
        }
        with self.assertRaises(Exception) as context:
            product.deserialize(data)
        self.assertIn("Invalid type for boolean [available]", str(context.exception))

    def test_deserialize_invalid_category(self):
        """It should raise DataValidationError for invalid category"""
        product = Product()
        data = {
            "name": "Weird Product",
            "description": "Just a test",
            "price": "10.00",
            "available": True,
            "category": "NOTREAL"  # This attribute doesn't exist in Category enum
        }
        with self.assertRaises(Exception) as context:
            product.deserialize(data)
        self.assertIn("Invalid attribute:", str(context.exception))

    def test_deserialize_none_data(self):
        """It should raise DataValidationError when no data (None) is passed"""
        product = Product()
        with self.assertRaises(Exception) as context:
            product.deserialize(None)
        self.assertIn("no data", str(context.exception).lower())

    def test_find_by_category_unknown(self):
        """It should Find Products with Category.UNKNOWN (and cover default param usage)"""
        product = ProductFactory(category=Category.UNKNOWN)
        product.id = None
        product.create()

        # Make sure we can find this product when we search by the UNKNOWN category
        found_products = Product.find_by_category(Category.UNKNOWN)
        self.assertEqual(found_products.count(), 1)
        self.assertEqual(found_products.first().id, product.id)
