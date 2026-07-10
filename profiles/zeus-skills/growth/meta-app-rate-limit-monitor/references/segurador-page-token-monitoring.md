# Segurador Page Token Monitoring — Session Notes

Context: Rodolfo tested a 1Password item named `Segurador Dân Kbang (B005) Token` with a user access token from a segurador profile that owns/has access to pages.

## Core distinction

App tokens / B001-B010 monitor app health and app roles. They do not automatically expose the pages inside each segurador profile.

Segurador user tokens can expose page-level data through `/me/accounts` when the user has page access and the token has the right scopes.

## Proven checks

Using the Dân Kbang token, these checks worked:

```text
/me                                      profile identity
/me/accounts?fields=id,name,category,tasks,access_token
/{page_id}?fields=id,name,category,fan_count,followers_count,verification_status,is_published,link
/{page_id}/conversations?fields=id,updated_time,message_count,unread_count,participants
/{conversation_id}/messages?fields=id,created_time,from,to,message,attachments,tags
/{page_id}/insights?metric=page_messages_new_conversations_unique,page_messages_total_messaging_connections&period=day
/{page_id}/posts?fields=id,message,created_time,permalink_url
/{page_id}/subscribed_apps
/{page_id}/leadgen_forms
```

Operationally useful fields:

```text
Page status:        is_published, verification_status, API accessibility
Audience:           fan_count, followers_count
Page permissions:   tasks such as MESSAGING, MANAGE, ANALYZE, ADVERTISE
Conversations:      participants, updated_time, message_count, unread_count
Messages:           from/to, message text, attachments, generic_template CTAs/postbacks
Messenger insights: new conversations / messaging connections where available
Subscribed app:     whether the bot/app is subscribed to the page
```

Never print user tokens, page tokens, app secrets, or raw credentials. It is OK to report token/page-token presence as boolean.

## Permissions observed as useful

For the tested token, these scopes were present and supported the page/conversation probes:

```text
pages_show_list
pages_read_engagement
pages_read_user_content
pages_messaging
pages_manage_metadata
pages_manage_posts
pages_manage_engagement
business_management
read_insights
pages_utility_messaging
```

For native Facebook Lead Forms, the missing permissions were fixed by adding:

```text
pages_manage_ads
leads_retrieval
```

After those were added, `/leadgen_forms` no longer returned the permission error. A page may still return `0` forms; that means no native Lead Forms are present for that page, not a permission failure.

## ChatPion/DigitalTrChat lead distinction

Rodolfo clarified that “lead” in this operation usually means a Messenger user that entered ChatPion/DigitalTrChat, not a native Meta Lead Form.

Use this source split:

```text
Meta Graph API        = pages, page access, conversations, messages, replies, CTAs/templates visible in messages, basic Messenger insights, page health symptoms.
ChatPion/DigitalTrChat = real bot subscriber/lead, tags, custom fields, sequence, campaign, delivery, opt-in/bot status.
Smart Bidding/quiz    = downstream click/flow/offer performance where applicable.
```

Do not claim Meta Graph alone can produce the definitive ChatPion lead count. It can infer conversation activity and show replies/buttons, but subscriber/lead status belongs to ChatPion/DigitalTrChat.

## Monitoring interpretation

Detectable or inferable via Meta token:

```text
Page disappeared / token lost page access      `/me/accounts` diff or page endpoint errors
Page unpublished/inaccessible                  `is_published=false` or API errors
Messaging access broken                         conversations/messages/subscribed_apps failures
User replied                                    conversation messages with external participant as sender
Button/template content                         message attachments/generic_template CTA/postback metadata
High unread backlog                             unread_count in conversations
Basic message volume                            insights/conversation counts
```

Not guaranteed directly by Meta Graph as a single field:

```text
temporary/permanent page restriction
message send restriction
ChatPion subscriber/lead count
who clicked every bot button when ChatPion handles the event internally
```

For those, combine Meta symptoms with ChatPion/DigitalTrChat delivery/subscriber data.
