# Request correlation contract

* Each request has a unique request ID, independent of session ID.
* One session may have multiple outstanding requests; a request may complete
  after a later request from the same session.
* Results may arrive in any order and must reach the originating session.
* An unknown response ID must raise UnknownResponse without consuming other
  pending calls.
* A duplicate outstanding request ID is rejected even across different
  sessions.
* Model policy and provider retry behaviour are not part of correlation.
