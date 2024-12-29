"use client";

import React, { useEffect, useState } from "react";
import { signIn } from "next-auth/react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";

const page = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const router = useRouter();

  const login = async (e) => {
    e.preventDefault();
    try {
      const loading = toast.loading("Login User...", {
        position: "top-center",
      });
      const response = await signIn("credentials", {
        username,
        password,
        redirect: false,
      });
      if (!response.ok) {
        toast.dismiss(loading);
        toast.error("Login Gagal.", { duration: 3000, position: "top-center" });
        return console.log(response.error);
      }
      toast.dismiss(loading);
      toast.success("Login Berhasil...", {
        duration: 3000,
        position: "top-center",
      });
      router.push("/");
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="center font-raleway">
      <form className="form-col" onSubmit={login}>
        <div className="form-item">
          <label className="label" htmlFor="username">
            Username
          </label>
          <input
            className="input"
            required
            onChange={(e) => setUsername(e.target.value)}
            value={username}
          />
        </div>
        <div className="form-item">
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            required
            className="input"
            type="password"
            onChange={(e) => setPassword(e.target.value)}
            value={password}
          />
        </div>
        <button className="btn" type="submit">
          Login
        </button>
      </form>
    </div>
  );
};

export default page;
