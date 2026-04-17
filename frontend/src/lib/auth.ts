import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { createServerClient } from "./supabase";
import bcrypt from "bcryptjs";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const supabase = createServerClient();
        const { data: user, error } = await supabase
          .from("users")
          .select("*")
          .eq("email", credentials.email as string)
          .single();

        if (error || !user) return null;

        const valid = await bcrypt.compare(
          credentials.password as string,
          user.hashed_password
        );
        if (!valid) return null;

        return {
          id: user.id,
          email: user.email,
          name: user.name || user.email,
        };
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/auth/login",
  },
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.userId = user.id;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.userId;
      }
      return session;
    },
  },
});
