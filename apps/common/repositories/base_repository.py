from django.db import transaction


class BaseRepository:
    model = None

    @classmethod
    def get(cls, pk):
        return cls.model.objects.filter(pk=pk).first()

    @classmethod
    def all(cls):
        return cls.model.objects.all()

    @classmethod
    def save(cls, instance):
        instance.save()
        return instance

    @classmethod
    def delete(cls, instance):
        instance.delete()

    @classmethod
    def exists(cls, **filters):
        return cls.model.objects.filter(**filters).exists()

    @classmethod
    @transaction.atomic
    def save_atomic(cls, instance):
        instance.save()
        return instance
