import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AdminShell } from "@/components/admin-shell";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const jar = await cookies();
  const token = jar.get("milan_admin_token")?.value;

  if (!token) {
    // Layout guard is a convenience only; every API call re-checks the role,
    // and the client 401 interceptor rotates the token via /auth/refresh.
    redirect("/admin/login");
  }

  return <AdminShell>{children}</AdminShell>;
}
