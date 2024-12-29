import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import axios from "axios";

const handler = new NextAuth({
  providers: [
    Credentials({
      name: "credentials",
      credentials: {},
      async authorize({ username, password }) {
        const response = await axios.post(
          "http://127.0.0.1:8080/api/v1/users/login",
          {
            username,
            password,
          }
        );
        if (!response.status === 200) {
          console.log(response.data.msg);
        }
        const user = response.data;
        user.email = "";
        if (user) {
          return user;
        }
        return null;
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 60 * 60 * 24,
  },
  pages: {
    signIn: "/",
  },
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async jwt({ token, user }) {
      console.log(user);
      if (user) {
        token.user = user;
      }

      return token;
    },

    async session({ session, token }) {
      session.user = token.user; // Add username to session

      return session;
    },
  },
});

export { handler as GET, handler as POST };
