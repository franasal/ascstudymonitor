""" Common interface for posting from a queue """

from ascmonitor import DocumentType
from ascmonitor.events import PostStartEvent, PostSuccessEvent, PostFailureEvent
from ascmonitor.post_queue import PostQueue
from ascmonitor.channels import PostSendException, SentPost
from ascmonitor.channels.twitter import TwitterChannel


class Poster:
    """ Posts documents to channels """

    def __init__(self, event_store, auths):
        self.event_store = event_store
        self.auths = auths
        self.queue = PostQueue(event_store)

        # init channels
        self.channels = {"twitter": TwitterChannel(**auths["twitter"])}

    def emit_start(self, document: DocumentType, channel: str):
        """ Notify event store about starting to post """
        event = PostStartEvent(document=document, channel=channel)
        self.event_store.put(event)

    def emit_success(self, document: DocumentType, post: SentPost, channel: str):
        """ Notify event store about a successful post """
        event = PostSuccessEvent(
            document=document, channel=channel, post=post.as_dict(), timestamp=post.created
        )
        self.event_store.put(event)

    def emit_fail(self, document: DocumentType, error: PostSendException, channel: str):
        """ Notify event store about a failed post """
        event = PostFailureEvent(
            document=document, error=error.message, allow_retry=error.allow_retry, channel=channel
        )
        self.event_store.put(event)

    def post(self, channels):
        """
        Post the next document in queue
        :param channels: List of channel names to post to
        """
        document = self.queue.pop()
        for channel_name in channels:
            channel = self.channels[channel_name]
            self.emit_start(document, channel_name)
            try:
                post = channel.format(document)
                post = channel.send(post)
                self.emit_success(document, post, channel_name)
            except PostSendException as error:
                self.emit_fail(document, error, channel_name)