import posthog from 'posthog-js';
export default function Page() {
  posthog.capture('page_view');
  return <form><input type="email" name="email" /><a href="/privacy">Privacy policy</a></form>;
}
