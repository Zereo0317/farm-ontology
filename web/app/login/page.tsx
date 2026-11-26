import type { Metadata } from "next";
import { cookies } from "next/headers";

import { advisoryCopy, type Locale } from "@/lib/copy";

const LOGIN_COPY: Record<Locale, { kicker: string; heading: string; sub: string; signIn: string; expired: string; setup: string; account: string }> = {
  "zh-TW": {
    kicker: "田間准入", heading: "田間入口", sub: "使用個人帳戶登入田間紀錄表",
    signIn: "使用安全登入", expired: "登入驗證未完成或已逾期，請再試一次。",
    setup: "登入服務尚未完成設定。", account: "每位使用者使用自己的帳戶；農場權限會另外核對。",
  },
  "zh-CN": {
    kicker: "田间准入", heading: "田间入口", sub: "使用个人账户登录田间记录表",
    signIn: "使用安全登录", expired: "登录验证未完成或已过期，请重试。",
    setup: "登录服务尚未完成设置。", account: "每位用户使用自己的账户；农场权限会另行核验。",
  },
  en: {
    kicker: "Farm access", heading: "Field entrance", sub: "Sign in to your field record with your own account",
    signIn: "Continue with secure sign-in", expired: "Sign-in did not complete or has expired. Please try again.",
    setup: "Sign-in is not configured yet.", account: "Each person uses an individual account. Farm access is checked separately.",
  },
  ja: {
    kicker: "ほ場アクセス", heading: "ほ場の入り口", sub: "個人アカウントでほ場記録にサインイン",
    signIn: "安全な方法でサインイン", expired: "サインインが完了しなかったか、有効期限が切れました。もう一度お試しください。",
    setup: "サインインはまだ設定されていません。", account: "利用者ごとに個人アカウントを使用します。ほ場の権限は別途確認されます。",
  },
  th: {
    kicker: "เข้าถึงแปลง", heading: "ทางเข้าแปลง", sub: "ลงชื่อเข้าใช้บันทึกแปลงด้วยบัญชีส่วนตัว",
    signIn: "ดำเนินการลงชื่อเข้าใช้อย่างปลอดภัย", expired: "การลงชื่อเข้าใช้ไม่เสร็จสมบูรณ์หรือหมดอายุแล้ว โปรดลองอีกครั้ง",
    setup: "ยังไม่ได้ตั้งค่าบริการลงชื่อเข้าใช้", account: "ผู้ใช้แต่ละคนใช้บัญชีของตนเอง และตรวจสอบสิทธิ์ฟาร์มแยกต่างหาก",
  },
};

export const metadata: Metadata = {
  title: "田間入口 · Sign in · ทางเข้าแปลง",
  robots: { index: false },
};

async function readLocale(): Promise<Locale> {
  const jar = await cookies();
  const saved = jar.get("farm-locale")?.value;
  return saved === "zh-TW" || saved === "zh-CN" || saved === "ja" || saved === "th" ? saved : "zh-TW";
}

function safeNext(raw: string | string[] | undefined): string {
  const value = typeof raw === "string" ? raw : "/";
  return value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\") && !/[\r\n\\]/.test(value)
    ? value
    : "/";
}

export default async function LoginPage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const next = safeNext(params.next);
  const locale = await readLocale();
  const copy = LOGIN_COPY[locale];
  const advisory = advisoryCopy[locale];
  const configured = Boolean(process.env.FARM_OIDC_ISSUER && process.env.FARM_OIDC_CLIENT_ID
    && process.env.FARM_OIDC_CLIENT_SECRET && process.env.FARM_OIDC_REDIRECT_URI
    && process.env.FARM_ACCESS_BUCKET
    && (process.env.FARM_SESSION_SECRET?.length ?? 0) >= 32);
  const failed = params.error === "state" || params.error === "sign-in";

  return (
    <main className="gate">
      <p className="kicker">{copy.kicker}</p>
      <h1>{copy.heading}<span>{copy.sub}</span></h1>
      {configured ? (
        <a className="primary" href={`/api/auth/login?next=${encodeURIComponent(next)}`}>{copy.signIn}</a>
      ) : (
        <p className="msg bad" role="status">{copy.setup}</p>
      )}
      {failed ? <p className="msg bad" role="alert">{copy.expired}</p> : null}
      <p className="caption">{copy.account}</p>
      <p className="caption">{advisory.licenceCaption} · use_class {advisory.screeningBadge}</p>
    </main>
  );
}
