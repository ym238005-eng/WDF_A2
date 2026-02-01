from django.test import TestCase, Client
from .models import User, UserProfile

class LibraryTest(TestCase):

    #Test Set Up 
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="James Alan",
            first_name="James",
            last_name="Alan",
            email="alan@gmail.com",
            password="lithan"
        )
        # We manually create the profile because your view logic requires it

        self.profile = UserProfile.objects.create(
            user=self.user,
            bio="My Feeling",
        )

    def test_sample(self):
        """This test will always pass just to prove the runner is working"""
        self.assertEqual(1, 1)