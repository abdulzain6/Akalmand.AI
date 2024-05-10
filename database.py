import contextlib
from peewee import *



class FileManager:
    def __init__(self, db: SqliteDatabase):
        class File(Model):
            file_owner = CharField()
            file_name = CharField()
            store_name = CharField()
            description = CharField(null=True)
            content = TextField(null=True)
            unique_id = CharField(primary_key=True, unique=True)


            class Meta:
                database = db

        self.model = File
        db.connect(reuse_if_open=True)
        db.create_tables([File], safe=True)

    def create_file(
        self,
        file_owner: str,
        file_name: str,
        description: str,
        content: str,
        unique_id: str,
        store_name: str,
    ):
        with contextlib.suppress(Exception):
            file = self.model(
                file_owner=file_owner,
                file_name=file_name,
                description=description,
                content=content,
                unique_id=unique_id,
                store_name=store_name,
            )
            file.save(force_insert=True)

    def read_file(self, unique_id: str):
        try:
            return self.model.get(self.model.unique_id == unique_id)
        except DoesNotExist:
            return None

    def update_file(self, unique_id: str, attributes: dict):
        file = self.model.get(self.model.unique_id == unique_id)
        for attr, value in attributes.items():
            setattr(file, attr, value)
        file.save()

    def delete_file(self, unique_id: str):
        file = self.model.get(self.model.unique_id == unique_id)
        file.delete_instance()

    def get_all_files(self) -> list:
        return list(self.model.select())

    def get_cls(self):
        return self.model

    def get_all_files_for_owner(self, file_owner: str) -> list:
        return list(self.model.select().where(self.model.file_owner == file_owner))

    def get_all_collections_for_owner(self, owner_name: str):
        return [
            record.store_name
            for record in (
                list(
                    self.model.select(self.model.store_name.distinct()).where(
                        self.model.file_owner == owner_name
                    )
                )
            )
        ]

    def get_all_files_for_collection(self, file_owner: str, store_name: str) -> list:
        return list(self.model.select().where(self.model.file_owner == file_owner and self.model.store_name == store_name))
    

