import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import axios from "axios";

const handler = new NextAuth({
  providers: [
    Credentials({
      name: "credentials",
      credentials: {},
      async authorize({ username, password }) {
        console.log("Authorize Section");
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
      if (!token.user) {
        token.user = user;
      } else {
        try {
          console.log(token.user);
          const response = await axios.get(
            `http://localhost:8080/api/v1/users/${token.user.userId}`
          );
          const newUserData = response.data;
          token.user = newUserData;
        } catch (error) {
          console.log(error);
        }
      }
      return token;
    },

    async session({ session, token }) {
      console.log("Session Section");
      session.user = token.user; // Add username to session

      return session;
    },
  },
});

export { handler as GET, handler as POST };
