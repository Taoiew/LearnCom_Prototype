const bcrypt = require("bcryptjs");
const fs = require("node:fs");
const path = require("node:path");
const { PrismaClient } = require("@prisma/client");
const { PrismaPg } = require("@prisma/adapter-pg");

const envPath = path.join(__dirname, "..", ".env");
if (fs.existsSync(envPath)) {
  const envFile = fs.readFileSync(envPath, "utf8");
  for (const line of envFile.split(/\r?\n/)) {
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)\s*$/);
    if (!match) continue;
    const [, key, rawValue] = match;
    if (process.env[key]) continue;
    process.env[key] = rawValue.replace(/^["']|["']$/g, "");
  }
}

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error("DATABASE_URL is required to seed users.");
}

const adapter = new PrismaPg({ connectionString: databaseUrl });
const prisma = new PrismaClient({ adapter });

async function upsertUser({ name, email, password, role }) {
  const hashedPassword = await bcrypt.hash(password, 12);
  await prisma.user.upsert({
    where: { email },
    create: {
      name,
      email,
      password: hashedPassword,
      role,
      language: "en",
    },
    update: {
      name,
      password: hashedPassword,
      role,
      language: "en",
    },
  });
}

async function main() {
  await upsertUser({
    name: "Teacher",
    email: "teacher@learning.com",
    password: "teacher1234",
    role: "TEACHER",
  });

  await upsertUser({
    name: "Student",
    email: "student@learning.com",
    password: "student1234",
    role: "STUDENT",
  });

  console.log("Seeded teacher@learning.com and student@learning.com");
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
