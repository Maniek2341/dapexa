from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from app.core.models import Company
from app.uzytkownik.default_role_groups import ensure_default_role_groups
from app.uzytkownik.models import CompanyRoleGroup

User = get_user_model()


def sync_role_group_members(role_group):
    matching_users = User.objects.filter(
        company_id=role_group.company_id,
        role=role_group.role,
    )
    role_group.group.user_set.set(matching_users)


def sync_user_role_groups(user):
    managed_group_ids = CompanyRoleGroup.objects.values_list("group_id", flat=True)
    matching_group_ids = CompanyRoleGroup.objects.filter(
        company_id=user.company_id,
        role=user.role,
    ).values_list("group_id", flat=True)

    user.groups.remove(*managed_group_ids)
    user.groups.add(*matching_group_ids)


@receiver(post_save, sender=CompanyRoleGroup)
def update_role_group_members(sender, instance, **kwargs):
    sync_role_group_members(instance)


@receiver(post_save, sender=User)
def update_user_role_groups(sender, instance, **kwargs):
    sync_user_role_groups(instance)


@receiver(post_delete, sender=CompanyRoleGroup)
def delete_backing_auth_group(sender, instance, **kwargs):
    Group.objects.filter(pk=instance.group_id).delete()


@receiver(post_save, sender=Company)
def create_default_groups_for_company(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: ensure_default_role_groups(instance)
        )


@receiver(post_migrate)
def create_missing_default_role_groups(sender, **kwargs):
    project_apps = [
        config
        for config in sender.apps.get_app_configs()
        if config.name.startswith("app.")
    ]
    if not project_apps or sender.name != project_apps[-1].name:
        return

    for company in Company.objects.iterator():
        ensure_default_role_groups(company)
