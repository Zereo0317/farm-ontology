import type { Metadata } from "next";
import { cookies } from "next/headers";

import { advisoryCopy, type Locale } from "@/lib/copy";

const LOGIN_COPY: Record<Locale, { kicker: string; heading: string; sub: string; label: string; enter: string; bad: string; crew: string }> = {
  "zh-TW": {
    kicker: "田間准入",
    heading: "田間入口",
    sub: "登入田間紀錄表",
    label: "通行碼",
    enter: "進入",
    bad: "通行碼不對，再試一次。",
    crew: "同一個通行碼由田務小組共用；登入一次可停留 30 天。",
  },
  "zh-CN": {
    kicker: "田间准入",
    heading: "田间入口",
    sub: "登录田间纪录表",
    label: "通行码",
    enter: "进入",
    bad: "通行码不对，再试一次。",
    crew: "同一个通行码由田务小组共用；登录一次可停留 30 天。",
  },
  en: {
    kicker: "Farm access",
    heading: "Field entrance",
    sub: "Sign in to the field sheet",
    label: "Access token",
    enter: "Enter",
    bad: "Wrong token, try again.",
    crew: "One shared token for the field crew; a sign-in lasts 30 days.",
  },
  ja: {
    kicker: "ほ場アクセス",
    heading: "ほ場の入り口",
    sub: "ほ場記録にサインイン",
    label: "アクセストークン",
    enter: "入る",
    bad: "トークンが違います。もう一度。",
    crew: "同じトークンを田園チームで共有。サインインは30日間有効。",
  },
  th: {
    kicker: "เข้าถึงแปลง",
    heading: "ทางเข้าแปลง",
    sub: "ลงชื่อเข้าใช้แบบฟอร์มบันทึกแปลง",
    label: "โทเคนเข้าใช้",
    enter: "เข้า",
    bad: "โทเคนไม่ถูกต้อง ลองอีกครั้ง",
    crew: "ทีมภาคสนามใช้โทเคนเดียวกัน ลงชื่อครั้งเดียวอยู่ได้ 30 วัน",
  },
};

export const metadata: Metadata = {
  title: "田間入口 · Sign in · ทางเข้าแปลง",
  robots: { index: false },
};

async function readLocale(): Promise<Locale> {
  const jar = await cookies();
  const saved = jar.get("farm-locale")?.value;
  return saved === "zh-TW" || saved === "zh-CN" || saved === "ja" || saved === "th"
    ? saved
    : "en";
}

export default async function LoginPage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const rawNext = typeof params.next === "string" ? params.next : "/";
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/";
  const failed = params.error === "1";
  const locale = await readLocale();
  const copy = LOGIN_COPY[locale];
  const advisory = advisoryCopy[locale];

  return (
    <main className="gate">
      <p className="kicker">{copy.kicker}</p>
      <h1>
        {copy.heading}
        <span>{copy.sub}</span>
      </h1>
      <form method="post" action="/api/access">
        <label htmlFor="token">{copy.label}</label>
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
          {copy.enter}
        </button>
        <p className={failed ? "msg bad" : "msg"}>{failed ? copy.bad : ""}</p>
      </form>
      <p className="caption">{copy.crew}</p>
      <p className="caption">
        {advisory.licenceCaption} · use_class {advisory.screeningBadge}
      </p>
    </main>
  );
}
