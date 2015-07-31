import logging

from django.core.exceptions import ObjectDoesNotExist

from .. import solitude

log = logging.getLogger(__name__)


def user_owns_resource(uri, lookup):
    """
    Returns True if a user owns a resource at URI.

    Get the resource at the URI filtered by the signed in user.
    If the filtered result is empty (404) it means the user does not
    own the resource.
    """
    owns_resource = False
    try:
        solitude.api().by_url(uri).get_object_or_404(**lookup)
        owns_resource = True
    except ObjectDoesNotExist, exc:
        log.debug('resource ownership check for {uri}: '
                  'catching {e.__class__.__name__}: {e}'
                  .format(uri=uri, e=exc))

    log.info('user owns resource? {} {} {}'
             .format(owns_resource, uri, lookup))

    return owns_resource
