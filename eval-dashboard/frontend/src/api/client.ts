import axios from "axios";
import { getRequesterId } from "../lib/session";

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((cfg) => {
  cfg.headers["X-Requester"] = getRequesterId();
  return cfg;
});
