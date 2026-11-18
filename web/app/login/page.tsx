import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "田間入口 · Sign in",
  robots: { index: false },
};

export default async function LoginPage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const rawNext = typeof params.next === "string" ? params.next : "/";
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/";
  const failed = params.error === "1";

  return (
    <main className="gate">
      <p className="kicker">Farm access</p>
      <h1>
        田間入口
        <span>sign in to the field sheet</span>
      </h1>
      <form method="post" action="/api/access">
        <label htmlFor="token">通行碼 Access token</label>
        <input
          id="token"
          name="token"
          type="password"
          autoFocus
          autoComplete="current-password"
          required
        />
        <input type="hidden" name="next" value={next} />
        <button className="primary" type="submit">
          進入 Enter
        </button>
        <p className={failed ? "msg bad" : "msg"}>
          {failed ? "通行碼不對，再試一次。Wrong token, try again." : ""}
        </p>
      </form>
      <p className="caption">
        同一個通行碼由田務小組共用；登入一次可停留 30 天。One shared token for
        the field crew; a sign-in lasts 30 days.
      </p>
    </main>
  );
}
