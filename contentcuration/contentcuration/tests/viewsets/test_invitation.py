from __future__ import absolute_import

import uuid

from django.urls import reverse

from contentcuration import models
from contentcuration.tests import testdata
from contentcuration.tests.base import StudioAPITestCase
from contentcuration.viewsets.sync.constants import INVITATION
from contentcuration.viewsets.sync.utils import generate_create_event
from contentcuration.viewsets.sync.utils import generate_delete_event
from contentcuration.viewsets.sync.utils import generate_update_event


class SyncTestCase(StudioAPITestCase):
    @property
    def sync_url(self):
        return reverse("sync")

    @property
    def invitation_metadata(self):
        return {
            "id": uuid.uuid4().hex,
            "channel": self.channel.id,
            "email": self.invited_user.email,
        }

    @property
    def invitation_db_metadata(self):
        return {
            "id": uuid.uuid4().hex,
            "channel_id": self.channel.id,
            "email": self.invited_user.email,
        }

    def setUp(self):
        super(SyncTestCase, self).setUp()
        self.channel = testdata.channel()
        self.user = testdata.user()
        self.channel.editors.add(self.user)
        self.invited_user = testdata.user("inv@inc.com")

    def test_create_invitation(self):
        self.client.force_authenticate(user=self.user)
        invitation = self.invitation_metadata
        response = self.client.post(
            self.sync_url,
            [generate_create_event(invitation["id"], INVITATION, invitation,)],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        try:
            models.Invitation.objects.get(id=invitation["id"])
        except models.Invitation.DoesNotExist:
            self.fail("Invitation was not created")

    def test_create_invitations(self):
        self.client.force_authenticate(user=self.user)
        invitation1 = self.invitation_metadata
        invitation2 = self.invitation_metadata
        response = self.client.post(
            self.sync_url,
            [
                generate_create_event(invitation1["id"], INVITATION, invitation1,),
                generate_create_event(invitation2["id"], INVITATION, invitation2,),
            ],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        try:
            models.Invitation.objects.get(id=invitation1["id"])
        except models.Invitation.DoesNotExist:
            self.fail("Invitation 1 was not created")

        try:
            models.Invitation.objects.get(id=invitation2["id"])
        except models.Invitation.DoesNotExist:
            self.fail("Invitation 2 was not created")

    def test_update_invitation_accept(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.sync_url,
            [generate_update_event(invitation.id, INVITATION, {"accepted": True},)],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        try:
            models.Invitation.objects.get(id=invitation.id)
            self.fail("Invitation was not deleted")
        except models.Invitation.DoesNotExist:
            pass
        self.assertTrue(self.channel.editors.filter(pk=self.invited_user.id).exists())
        self.assertFalse(
            models.Invitation.objects.filter(
                email=self.invited_user.email, channel=self.channel
            ).exists()
        )

    def test_update_invitation_decline(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.sync_url,
            [generate_update_event(invitation.id, INVITATION, {"declined": True},)],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        try:
            models.Invitation.objects.get(id=invitation.id)
            self.fail("Invitation was not deleted")
        except models.Invitation.DoesNotExist:
            pass
        self.assertFalse(self.channel.editors.filter(pk=self.invited_user.id).exists())
        self.assertFalse(
            models.Invitation.objects.filter(
                email=self.invited_user.email, channel=self.channel
            ).exists()
        )

    def test_update_invitation_empty(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.sync_url,
            [generate_update_event(invitation.id, INVITATION, {},)],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_update_invitation_unwriteable_fields(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.sync_url,
            [
                generate_update_event(
                    invitation.id, INVITATION, {"not_a_field": "not_a_value"},
                )
            ],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_delete_invitation(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.sync_url,
            [generate_delete_event(invitation.id, INVITATION,)],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        try:
            models.Invitation.objects.get(id=invitation.id)
            self.fail("Invitation was not deleted")
        except models.Invitation.DoesNotExist:
            pass

    def test_delete_invitations(self):
        invitation1 = models.Invitation.objects.create(**self.invitation_db_metadata)

        invitation2 = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.sync_url,
            [
                generate_delete_event(invitation1.id, INVITATION,),
                generate_delete_event(invitation2.id, INVITATION,),
            ],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        try:
            models.Invitation.objects.get(id=invitation1.id)
            self.fail("Invitation 1 was not deleted")
        except models.Invitation.DoesNotExist:
            pass

        try:
            models.Invitation.objects.get(id=invitation2.id)
            self.fail("Invitation 2 was not deleted")
        except models.Invitation.DoesNotExist:
            pass


class CRUDTestCase(StudioAPITestCase):
    @property
    def invitation_metadata(self):
        return {
            "id": uuid.uuid4().hex,
            "channel": self.channel.id,
            "email": self.invited_user.email,
        }

    @property
    def invitation_db_metadata(self):
        return {
            "id": uuid.uuid4().hex,
            "channel_id": self.channel.id,
            "email": self.invited_user.email,
        }

    def setUp(self):
        super(CRUDTestCase, self).setUp()
        self.channel = testdata.channel()
        self.user = testdata.user()
        self.channel.editors.add(self.user)
        self.invited_user = testdata.user("inv@inc.com")

    def test_create_invitation(self):
        self.client.force_authenticate(user=self.user)
        invitation = self.invitation_metadata
        response = self.client.post(
            reverse("invitation-list"), invitation, format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        try:
            models.Invitation.objects.get(id=invitation["id"])
        except models.Invitation.DoesNotExist:
            self.fail("Invitation was not created")

    def test_create_invitation_no_channel_permission(self):
        self.client.force_authenticate(user=self.user)
        new_channel = testdata.channel()
        invitation = self.invitation_metadata
        invitation["channel"] = new_channel.id
        response = self.client.post(
            reverse("invitation-list"), invitation, format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_update_invitation_accept(self):
        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("invitation-detail", kwargs={"pk": invitation.id}),
            {"accepted": True},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
        try:
            models.Invitation.objects.get(id=invitation.id)
            self.fail("Invitation was not deleted")
        except models.Invitation.DoesNotExist:
            pass

        self.assertTrue(self.channel.editors.filter(pk=self.invited_user.id).exists())
        self.assertFalse(
            models.Invitation.objects.filter(
                email=self.invited_user.email, channel=self.channel
            ).exists()
        )

    def test_update_invitation_decline(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("invitation-detail", kwargs={"pk": invitation.id}),
            {"declined": True},
            format="json",
        )
        self.assertEqual(response.status_code, 204, response.content)
        try:
            models.Invitation.objects.get(id=invitation.id)
            self.fail("Invitation was not deleted")
        except models.Invitation.DoesNotExist:
            pass
        self.assertFalse(self.channel.editors.filter(pk=self.invited_user.id).exists())
        self.assertFalse(
            models.Invitation.objects.filter(
                email=self.invited_user.email, channel=self.channel
            ).exists()
        )

    def test_update_invitation_empty(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("invitation-detail", kwargs={"pk": invitation.id}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_update_invitation_unwriteable_fields(self):

        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("invitation-detail", kwargs={"pk": invitation.id}),
            {"not_a_field": "not_a_value"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_delete_invitation(self):
        invitation = models.Invitation.objects.create(**self.invitation_db_metadata)

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            reverse("invitation-detail", kwargs={"pk": invitation.id})
        )
        self.assertEqual(response.status_code, 204, response.content)
        try:
            models.Invitation.objects.get(id=invitation.id)
            self.fail("Invitation was not deleted")
        except models.Invitation.DoesNotExist:
            pass
