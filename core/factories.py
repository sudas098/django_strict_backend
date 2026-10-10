import factory

from core.models import CustomUser


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):  # type: ignore[no-untyped-def]
        password = kwargs.pop("password", "TestPassword123!")
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, password=password, **kwargs)
