# Copyright (c) 2023 Airbyte, Inc., all rights reserved.

from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch

import freezegun

from airbyte_cdk.models import AirbyteStateBlob, AirbyteStreamStatus, SyncMode
from airbyte_cdk.models import Level as LogLevel
from airbyte_cdk.test.mock_http import HttpMocker
from airbyte_cdk.test.mock_http.response_builder import FieldPath
from airbyte_cdk.test.state_builder import StateBuilder
from airbyte_cdk.utils.datetime_helpers import ab_datetime_now, ab_datetime_parse

from .config import ConfigBuilder
from .helpers import given_post_comments, given_posts, given_ticket_forms
from .utils import datetime_to_string, get_log_messages_by_log_level, read_stream, string_to_datetime
from .zs_requests import PostCommentVotesRequestBuilder
from .zs_requests.request_authenticators import ApiTokenAuthenticator
from .zs_responses import ErrorResponseBuilder, PostCommentVotesResponseBuilder
from .zs_responses.records import PostCommentVotesRecordBuilder


_NOW = datetime.now(timezone.utc)


@freezegun.freeze_time(_NOW.isoformat())
class TestPostsCommentVotesStreamFullRefresh(TestCase):
    @property
    def _config(self):
        return (
            ConfigBuilder()
            .with_basic_auth_credentials("user@example.com", "password")
            .with_subdomain("d3v-airbyte")
            .with_start_date(ab_datetime_now().subtract(timedelta(weeks=104)))
            .build()
        )

    def get_authenticator(self, config):
        return ApiTokenAuthenticator(email=config["credentials"]["email"], password=config["credentials"]["api_token"])

    @HttpMocker()
    def test_given_one_page_when_read_posts_comments_votes_then_return_records(self, http_mocker):
        """
        A normal full refresh sync without pagination
        """
        api_token_authenticator = self.get_authenticator(self._config)
        # todo: Add this back once the CDK supports conditional streams on an endpoint
        # _ = given_ticket_forms(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)

        posts_record_builder = given_posts(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)
        post = posts_record_builder.build()

        posts_comments_record_builder = given_post_comments(
            http_mocker, string_to_datetime(self._config["start_date"]), post["id"], api_token_authenticator
        )
        post_comment = posts_comments_record_builder.build()

        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_start_time(self._config["start_date"])
            .with_page_size(100)
            .build(),
            PostCommentVotesResponseBuilder.post_comment_votes_response()
            .with_record(PostCommentVotesRecordBuilder.post_commetn_votes_record())
            .build(),
        )

        output = read_stream("post_comment_votes", SyncMode.full_refresh, self._config)
        assert len(output.records) == 1

    @HttpMocker()
    def test_given_403_error_when_read_posts_comments_then_skip_stream(self, http_mocker):
        """
        Get a 403 error and then skip the stream
        """
        api_token_authenticator = self.get_authenticator(self._config)
        # todo: Add this back once the CDK supports conditional streams on an endpoint
        # _ = given_ticket_forms(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)

        posts_record_builder = given_posts(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)
        post = posts_record_builder.build()

        posts_comments_record_builder = given_post_comments(
            http_mocker, string_to_datetime(self._config["start_date"]), post["id"], api_token_authenticator
        )
        post_comment = posts_comments_record_builder.build()

        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_start_time(self._config["start_date"])
            .with_page_size(100)
            .build(),
            ErrorResponseBuilder.response_with_status(403).build(),
        )

        output = read_stream("post_comment_votes", SyncMode.full_refresh, self._config)
        assert len(output.records) == 0
        assert output.get_stream_statuses("post_comment_votes")[-1] == AirbyteStreamStatus.INCOMPLETE
        assert any(
            [
                "failed with status code '403' and error message" in error
                for error in get_log_messages_by_log_level(output.logs, LogLevel.ERROR)
            ]
        )

    @HttpMocker()
    def test_given_404_error_when_read_posts_comments_then_skip_stream(self, http_mocker):
        """
        Get a 404 error and then skip the stream
        """
        api_token_authenticator = self.get_authenticator(self._config)
        # todo: Add this back once the CDK supports conditional streams on an endpoint
        # _ = given_ticket_forms(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)

        posts_record_builder = given_posts(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)
        post = posts_record_builder.build()

        posts_comments_record_builder = given_post_comments(
            http_mocker, string_to_datetime(self._config["start_date"]), post["id"], api_token_authenticator
        )
        post_comment = posts_comments_record_builder.build()

        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_start_time(self._config["start_date"])
            .with_page_size(100)
            .build(),
            ErrorResponseBuilder.response_with_status(404).build(),
        )

        output = read_stream("post_comment_votes", SyncMode.full_refresh, self._config)
        assert len(output.records) == 0
        assert output.get_stream_statuses("post_comment_votes")[-1] == AirbyteStreamStatus.INCOMPLETE
        assert any(
            [
                "failed with status code '404' and error message" in error
                for error in get_log_messages_by_log_level(output.logs, LogLevel.ERROR)
            ]
        )

    @HttpMocker()
    def test_given_500_error_when_read_posts_comments_then_stop_syncing(self, http_mocker):
        """
        Get a 500 error and then stop syncing
        """
        api_token_authenticator = self.get_authenticator(self._config)
        # todo: Add this back once the CDK supports conditional streams on an endpoint
        # _ = given_ticket_forms(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)

        posts_record_builder = given_posts(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)
        post = posts_record_builder.build()

        posts_comments_record_builder = given_post_comments(
            http_mocker, string_to_datetime(self._config["start_date"]), post["id"], api_token_authenticator
        )
        post_comment = posts_comments_record_builder.build()

        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_start_time(self._config["start_date"])
            .with_page_size(100)
            .build(),
            ErrorResponseBuilder.response_with_status(500).build(),
        )

        with patch("time.sleep", return_value=None):
            output = read_stream("post_comment_votes", SyncMode.full_refresh, self._config)

        assert len(output.records) == 0

        error_logs = get_log_messages_by_log_level(output.logs, LogLevel.ERROR)
        assert any(["Internal server error" in error for error in error_logs])


@freezegun.freeze_time(_NOW.isoformat())
class TestPostsCommentVotesStreamIncremental(TestCase):
    @property
    def _config(self):
        return (
            ConfigBuilder()
            .with_basic_auth_credentials("user@example.com", "password")
            .with_subdomain("d3v-airbyte")
            .with_start_date(ab_datetime_now().subtract(timedelta(weeks=104)))
            .build()
        )

    def _get_authenticator(self, config):
        return ApiTokenAuthenticator(email=config["credentials"]["email"], password=config["credentials"]["api_token"])

    @HttpMocker()
    def test_given_no_state_and_successful_sync_when_read_then_set_state_to_now(self, http_mocker):
        """
        A normal incremental sync without pagination
        """
        api_token_authenticator = self._get_authenticator(self._config)
        # todo: Add this back once the CDK supports conditional streams on an endpoint
        # _ = given_ticket_forms(http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator)

        post_updated_at = string_to_datetime(self._config["start_date"]).add(timedelta(minutes=5))
        posts_record_builder = given_posts(
            http_mocker, string_to_datetime(self._config["start_date"]), api_token_authenticator, post_updated_at
        )
        post = posts_record_builder.build()

        post_comments_updated_at = string_to_datetime(self._config["start_date"]).add(timedelta(minutes=10))
        post_comments_record_builder = given_post_comments(
            http_mocker,
            string_to_datetime(self._config["start_date"]),
            post["id"],
            api_token_authenticator,
            post_comments_updated_at,
        )
        post_comment = post_comments_record_builder.build()

        post_comment_votes_record_builder = PostCommentVotesRecordBuilder.post_commetn_votes_record()
        post_comment_votes = post_comment_votes_record_builder.build()

        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_start_time(self._config["start_date"])
            .with_page_size(100)
            .build(),
            PostCommentVotesResponseBuilder.post_comment_votes_response()
            .with_record(PostCommentVotesRecordBuilder.post_commetn_votes_record())
            .build(),
        )

        output = read_stream("post_comment_votes", SyncMode.incremental, self._config)
        assert len(output.records) == 1

        assert output.most_recent_state.stream_descriptor.name == "post_comment_votes"
        post_comment_votes_state_value = str(int(string_to_datetime(post_comment_votes["updated_at"]).timestamp()))
        assert output.most_recent_state.stream_state == AirbyteStateBlob(
            {
                "use_global_cursor": False,
                "states": [
                    {
                        "partition": {
                            "id": {"comment_id": post_comment["id"], "post_id": post["id"]},
                            "parent_slice": {"parent_slice": {}, "post_id": post["id"]},
                        },
                        "cursor": {"updated_at": post_comment_votes_state_value},
                    }
                ],
                "state": {"updated_at": post_comment_votes_state_value},
                "lookback_window": 0,
                "parent_state": {
                    "post_comments": {
                        "use_global_cursor": False,
                        "state": {"updated_at": datetime_to_string(post_comments_updated_at)},
                        "lookback_window": 0,
                        "states": [
                            {
                                "partition": {"parent_slice": {}, "post_id": post["id"]},
                                "cursor": {"updated_at": datetime_to_string(post_comments_updated_at)},
                            }
                        ],
                        "parent_state": {"posts": {"updated_at": datetime_to_string(post_updated_at)}},
                    }
                },
            }
        )

    @HttpMocker()
    def test_given_state_and_pagination_when_read_then_return_records(self, http_mocker):
        """
        A normal incremental sync with state and pagination
        """
        api_token_authenticator = self._get_authenticator(self._config)

        state_start_date = ab_datetime_parse(self._config["start_date"]).add(timedelta(weeks=52))
        first_page_record_updated_at = state_start_date.add(timedelta(weeks=4))
        last_page_record_updated_at = first_page_record_updated_at.add(timedelta(weeks=8))

        state = {"updated_at": datetime_to_string(state_start_date)}

        post_updated_at = state_start_date.add(timedelta(minutes=5))
        posts_record_builder = given_posts(http_mocker, state_start_date, api_token_authenticator, post_updated_at)
        post = posts_record_builder.build()

        post_comments_updated_at = state_start_date.add(timedelta(minutes=10))
        post_comments_record_builder = given_post_comments(
            http_mocker,
            state_start_date,
            post["id"],
            api_token_authenticator,
            post_comments_updated_at,
        )
        post_comment = post_comments_record_builder.build()

        post_comment_votes_first_record_builder = PostCommentVotesRecordBuilder.post_commetn_votes_record().with_field(
            FieldPath("updated_at"), datetime_to_string(first_page_record_updated_at)
        )

        # Read first page request mock
        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_start_time(datetime_to_string(state_start_date))
            .with_page_size(100)
            .build(),
            PostCommentVotesResponseBuilder.post_comment_votes_response(
                PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
                .with_page_size(100)
                .build()
            )
            .with_pagination()
            .with_record(post_comment_votes_first_record_builder)
            .build(),
        )

        post_comment_votes_last_record_builder = (
            PostCommentVotesRecordBuilder.post_commetn_votes_record()
            .with_id("last_record_id_from_last_page")
            .with_field(FieldPath("updated_at"), datetime_to_string(last_page_record_updated_at))
        )

        # Read second page request mock
        http_mocker.get(
            PostCommentVotesRequestBuilder.post_comment_votes_endpoint(api_token_authenticator, post["id"], post_comment["id"])
            .with_page_after("after-cursor")
            .with_page_size(100)
            .build(),
            PostCommentVotesResponseBuilder.post_comment_votes_response().with_record(post_comment_votes_last_record_builder).build(),
        )

        output = read_stream(
            "post_comment_votes", SyncMode.incremental, self._config, StateBuilder().with_stream_state("post_comment_votes", state).build()
        )
        assert len(output.records) == 2

        assert output.most_recent_state.stream_descriptor.name == "post_comment_votes"
        post_comment_votes_state_value = str(
            int(string_to_datetime(post_comment_votes_last_record_builder.build()["updated_at"]).timestamp())
        )
        assert output.most_recent_state.stream_state == AirbyteStateBlob(
            {
                "use_global_cursor": False,
                "states": [
                    {
                        "partition": {
                            "id": {"comment_id": post_comment["id"], "post_id": post["id"]},
                            "parent_slice": {"parent_slice": {}, "post_id": post["id"]},
                        },
                        "cursor": {"updated_at": post_comment_votes_state_value},
                    }
                ],
                "state": {"updated_at": post_comment_votes_state_value},
                "lookback_window": 0,
                "parent_state": {
                    "post_comments": {
                        "use_global_cursor": False,
                        "state": {"updated_at": datetime_to_string(post_comments_updated_at)},
                        "lookback_window": 0,
                        "states": [
                            {
                                "partition": {"parent_slice": {}, "post_id": post["id"]},
                                "cursor": {"updated_at": datetime_to_string(post_comments_updated_at)},
                            }
                        ],
                        "parent_state": {"posts": {"updated_at": datetime_to_string(post_updated_at)}},
                    }
                },
            }
        )
