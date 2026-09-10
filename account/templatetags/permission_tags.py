from django import template

register = template.Library()

@register.simple_tag
def user_has_permission(user, perm):
    # print("user.has_perm(perm)",user.has_perm(perm))
    return user.has_perm(perm)


@register.filter
def is_active_route(current_url_name, url_names_str):
    if not current_url_name:
        return False
    allowed_urls = [u.strip() for u in url_names_str.split() if u.strip()]
    return current_url_name in allowed_urls