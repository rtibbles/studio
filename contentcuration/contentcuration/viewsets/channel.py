from django.conf import settings
from django.db.models import BooleanField
from django.db.models import IntegerField
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import Value
from django.db.models.functions import Cast
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import BooleanFilter
from django_filters.rest_framework import CharFilter
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import FilterSet
from le_utils.constants import content_kinds
from le_utils.constants import roles
from rest_framework import serializers
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from contentcuration.decorators import cache_no_user_data
from contentcuration.models import Channel
from contentcuration.models import ContentNode
from contentcuration.models import get_channel_thumbnail
from contentcuration.models import SecretToken
from contentcuration.models import User
from contentcuration.viewsets.base import BulkModelSerializer
from contentcuration.viewsets.base import BulkListSerializer
from contentcuration.viewsets.base import ValuesViewset
from contentcuration.viewsets.common import ContentDefaultsSerializer


class CatalogListPagination(PageNumberPagination):
    page_size = None
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "page_number": self.page.number,
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "results": data,
            }
        )


class ChannelFilter(FilterSet):
    edit = BooleanFilter(method="filter_edit")
    view = BooleanFilter(method="filter_view")
    bookmark = BooleanFilter(method="filter_bookmark")
    published = BooleanFilter(method="filter_published")
    ids = CharFilter(method="filter_ids")
    keywords = CharFilter(method="filter_keywords")
    language = CharFilter(method="filter_language")
    licenses = CharFilter(method="filter_licenses")
    kinds = CharFilter(method="filter_kinds")
    coach = BooleanFilter(method="filter_coach")
    assessments = BooleanFilter(method="filter_assessments")
    subtitles = BooleanFilter(method="filter_subtitles")
    bookmark = BooleanFilter(method="filter_bookmark")
    published = BooleanFilter(method="filter_published")

    def __init__(self, *args, **kwargs):
        super(ChannelFilter, self).__init__(*args, **kwargs)
        self.main_tree_query = ContentNode.objects.filter(
            tree_id=OuterRef("main_tree__tree_id")
        )

    def filter_keywords(self, queryset, name, value):
        keywords_query = self.main_tree_query.filter(
            Q(tags__tag_name__icontains=value)
            | Q(author__icontains=value)
            | Q(aggregator__icontains=value)
            | Q(provider__icontains=value)
        )
        return queryset.annotate(
            keyword_match_count=SQCount(keywords_query, field="content_id"),
            primary_token=Max("secret_tokens__token"),
        ).filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(pk__istartswith=value)
            | Q(primary_token=value.replace("-", ""))
            | Q(keyword_match_count__gt=0)
        )

    def filter_language(self, queryset, name, value):
        language_query = (
            self.main_tree_query.filter(language_id=value)
            .values("content_id")
            .distinct()
        )
        return queryset.annotate(
            language_count=SQCount(language_query, field="content_id")
        ).filter(Q(language_id=value) | Q(language_count__gt=0))

    def filter_licenses(self, queryset, name, value):
        license_query = (
            self.main_tree_query.filter(
                license_id__in=[int(l) for l in value.split(",")]
            )
            .values("content_id")
            .distinct()
        )
        return queryset.annotate(
            license_count=SQCount(license_query, field="content_id")
        ).exclude(license_count=0)

    def filter_kinds(self, queryset, name, value):
        kinds_query = (
            self.main_tree_query.filter(kind_id__in=value.split(","))
            .values("content_id")
            .distinct()
        )
        return queryset.annotate(
            kind_match_count=SQCount(kinds_query, field="content_id")
        ).exclude(kind_match_count=0)

    def filter_coach(self, queryset, name, value):
        coach_query = self.main_tree_query.filter(role_visibility=roles.COACH)
        return queryset.annotate(
            coach_count=SQCount(coach_query, field="content_id")
        ).exclude(coach_count=0)

    def filter_assessments(self, queryset, name, value):
        assessment_query = self.main_tree_query.filter(kind_id=content_kinds.EXERCISE)
        return queryset.annotate(
            assessment_count=SQCount(assessment_query, field="content_id")
        ).exclude(assessment_count=0)

    def filter_subtitles(self, queryset, name, value):
        subtitle_query = self.main_tree_query.filter(files__preset__subtitle=True)
        return queryset.annotate(
            subtitle_count=SQCount(subtitle_query, field="content_id")
        ).exclude(subtitle_count=0)

    def filter_edit(self, queryset, name, value):
        return queryset.filter(edit=True)

    def filter_view(self, queryset, name, value):
        return queryset.filter(view=True)

    def filter_bookmark(self, queryset, name, value):
        return queryset.filter(bookmark=True)

    def filter_published(self, queryset, name, value):
        return queryset.filter(main_tree__published=True)

    def filter_ids(self, queryset, name, value):
        try:
            # Limit SQL params to 50 - shouldn't be fetching this many
            # ids at once
            return queryset.filter(pk__in=value.split(",")[:50])
        except ValueError:
            # Catch in case of a poorly formed UUID
            return queryset.none()

    class Meta:
        model = Channel
        fields = (
            "keywords",
            "published",
            "language",
            "licenses",
            "kinds",
            "coach",
            "assessments",
            "subtitles",
            "bookmark",
            "edit",
            "view",
            "public",
            "ids",
        )


class SQCount(Subquery):
    # Include ALIAS at the end to support Postgres
    template = "(SELECT COUNT(%(field)s) FROM (%(subquery)s) AS %(field)s__sum)"
    output_field = IntegerField()


class ChannelSerializer(BulkModelSerializer):
    """
    This is a write only serializer - we leverage it to do create and update
    operations, but read operations are handled by the Viewset.
    """

    bookmark = serializers.BooleanField()
    content_defaults = ContentDefaultsSerializer(partial=True)

    class Meta:
        model = Channel
        fields = (
            "id",
            "deleted",
            "name",
            "description",
            "thumbnail",
            "thumbnail_encoding",
            "version",
            "language",
            "bookmark",
            "content_defaults",
        )
        list_serializer_class = BulkListSerializer
        nested_writes = True

    def create(self, validated_data):
        bookmark = validated_data.pop("bookmark", None)
        content_defaults = validated_data.pop("content_defaults", {})
        validated_data["content_defaults"] = self.fields["content_defaults"].create(content_defaults)
        if "request" in self.context:
            user_id = self.context["request"].user.id
            # This has been newly created so add the current user as an editor
            validated_data["editors"] = [user_id]
            if bookmark:
                validated_data["bookmarked_by"] = [user_id]
        return super(ChannelSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        bookmark = validated_data.pop("bookmark", None)
        content_defaults = validated_data.pop("content_defaults", None)
        if content_defaults is not None:
            validated_data["content_defaults"] = self.fields["content_defaults"].update(instance.content_defaults, content_defaults)
        if "request" in self.context:
            user_id = self.context["request"].user.id
            # We could possibly do this in bulk later in the process,
            # but bulk creating many to many through table models
            # would be required, and that would need us to be able to
            # efficiently ignore conflicts with existing models.
            # When we have upgraded to Django 2.2, we can do the bulk
            # creation of many to many models to make this more efficient
            # and use the `ignore_conflicts=True` kwarg to ignore
            # any conflicts.
            if bookmark is not None and bookmark:
                instance.bookmarked_by.add(user_id)
            elif bookmark is not None:
                instance.bookmarked_by.remove(user_id)
        return super(ChannelSerializer, self).update(instance, validated_data)


class ChannelViewSet(ValuesViewset):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    permission_classes = [AllowAny]
    pagination_class = CatalogListPagination
    filter_class = ChannelFilter
    values = (
        "id",
        "name",
        "description",
        "main_tree__published",
        "thumbnail",
        "thumbnail_encoding",
        "language",
        "primary_token",
        "count",
        "modified",
        "count",
        "view",
        "edit",
        "bookmark",
        "public",
        "version",
        "main_tree__created",
        "last_published",
        "ricecooker_version",
        "main_tree__id",
        "content_defaults",
        "deleted",
    )

    field_map = {
        "thumbnail_url": get_channel_thumbnail,
        "published": "main_tree__published",
        "created": "main_tree__created",
        "root_id": "main_tree__id",
    }

    def get_queryset(self):
        user_id = not self.request.user.is_anonymous() and self.request.user.id
        queryset = Channel.objects.filter(
            id__in=Channel.objects.filter(deleted=False)
            .filter(Q(editors=user_id) | Q(viewers=user_id) | Q(public=True))
            .values_list("id", flat=True)
            .distinct()
        )

        # Annotate edit, view, and bookmark onto the channels
        # Have to cast to integer first as it initially gets set
        # as a Big Integer, which cannot be cast directly to a Boolean
        # We do this here, rather than in the annotate_queryset as these are
        # used during the filtering of the queryset also.
        user_queryset = User.objects.filter(id=user_id)
        queryset = queryset.annotate(
            edit=Cast(
                Cast(
                    SQCount(
                        user_queryset.filter(editable_channels=OuterRef("id")),
                        field="id",
                    ),
                    IntegerField(),
                ),
                BooleanField(),
            ),
            view=Cast(
                Cast(
                    SQCount(
                        user_queryset.filter(view_only_channels=OuterRef("id")),
                        field="id",
                    ),
                    IntegerField(),
                ),
                BooleanField(),
            ),
            bookmark=Cast(
                Cast(
                    SQCount(
                        user_queryset.filter(bookmarked_channels=OuterRef("id")),
                        field="id",
                    ),
                    IntegerField(),
                ),
                BooleanField(),
            ),
        )

        return queryset.order_by("-priority", "name")

    def prefetch_queryset(self, queryset):
        prefetch_secret_token = Prefetch(
            "secret_tokens", queryset=SecretToken.objects.filter(is_primary=True)
        )
        queryset = queryset.select_related("language", "main_tree").prefetch_related(
            prefetch_secret_token
        )
        return queryset

    def annotate_queryset(self, queryset):
        queryset = queryset.annotate(primary_token=Max("secret_tokens__token"))
        channel_main_tree_nodes = ContentNode.objects.filter(
            tree_id=OuterRef("main_tree__tree_id")
        )
        # Add the last modified node modified value as the channel last modified
        queryset = queryset.annotate(
            modified=Subquery(
                channel_main_tree_nodes.values("modified").order_by("-modified")[:1]
            )
        )
        # Add the unique count of distinct non-topic node content_ids
        non_topic_content_ids = (
            channel_main_tree_nodes.exclude(kind_id=content_kinds.TOPIC)
            .order_by("content_id")
            .distinct("content_id")
            .values_list("content_id", flat=True)
        )

        queryset = queryset.annotate(
            count=SQCount(non_topic_content_ids, field="content_id")
        )
        return queryset


@method_decorator(cache_page(settings.PUBLIC_CHANNELS_CACHE_DURATION, key_prefix='public_catalog_list'), name="dispatch")
@method_decorator(cache_no_user_data, name="dispatch")
class CatalogViewSet(ChannelViewSet):
    pagination_class = CatalogListPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Channel.objects.filter(deleted=False, public=True).annotate(
            edit=Value(
                False,
                BooleanField(),
            ),
            view=Value(
                False,
                BooleanField(),
            ),
            bookmark=Value(
                False,
                BooleanField(),
            ),
        )

        return queryset.order_by("-priority", "name")