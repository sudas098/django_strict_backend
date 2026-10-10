import factory

from core.factories import UserFactory
from documents.models import Document, DocumentMember, DocumentRole


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Faker("sentence", nb_words=4)
    content = factory.Faker("paragraph")
    owner = factory.SubFactory(UserFactory)


class DocumentMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentMember

    document = factory.SubFactory(DocumentFactory)
    user = factory.SubFactory(UserFactory)
    role = DocumentRole.VIEWER
