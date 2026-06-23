--
-- PostgreSQL database dump
--

\restrict mLiWvKSIS1wIjugIRno1X8BaODFTHp1rk9FfhpDtc6C2Y7eivmcosNsygVLRSNU

-- Dumped from database version 18.4 (Debian 18.4-1.pgdg12+1)
-- Dumped by pg_dump version 18.4 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: contest_participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contest_participants (
    id integer NOT NULL,
    contest_id integer NOT NULL,
    user_id integer NOT NULL,
    joined_at timestamp with time zone DEFAULT now()
);


--
-- Name: contest_participants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contest_participants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contest_participants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contest_participants_id_seq OWNED BY public.contest_participants.id;


--
-- Name: contest_problems; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contest_problems (
    id integer NOT NULL,
    contest_id integer NOT NULL,
    problem_id integer NOT NULL,
    points integer DEFAULT 100
);


--
-- Name: contest_problems_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contest_problems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contest_problems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contest_problems_id_seq OWNED BY public.contest_problems.id;


--
-- Name: contests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contests (
    id integer NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    invite_code character varying(20) NOT NULL,
    created_by integer NOT NULL,
    duration_minutes integer DEFAULT 60,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    is_public boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: contests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contests_id_seq OWNED BY public.contests.id;


--
-- Name: problems; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.problems (
    id integer NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    difficulty character varying(10),
    created_at timestamp with time zone DEFAULT now(),
    category character varying(100)
);


--
-- Name: problems_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.problems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: problems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.problems_id_seq OWNED BY public.problems.id;


--
-- Name: submissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.submissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    problem_id integer NOT NULL,
    language character varying(20) NOT NULL,
    code text NOT NULL,
    status character varying(20),
    verdict character varying(30),
    runtime_ms double precision,
    memory_kb integer,
    error_output text,
    created_at timestamp with time zone DEFAULT now(),
    judged_at timestamp with time zone,
    ai_review text
);


--
-- Name: submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.submissions_id_seq OWNED BY public.submissions.id;


--
-- Name: test_cases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_cases (
    id integer NOT NULL,
    problem_id integer NOT NULL,
    stdin text NOT NULL,
    expected text NOT NULL,
    is_sample integer
);


--
-- Name: test_cases_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.test_cases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: test_cases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.test_cases_id_seq OWNED BY public.test_cases.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    password character varying(255),
    created_at timestamp with time zone DEFAULT now(),
    is_admin boolean DEFAULT false NOT NULL,
    google_id character varying(255),
    profile_picture text,
    date_of_birth character varying(20)
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: contest_participants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest_participants ALTER COLUMN id SET DEFAULT nextval('public.contest_participants_id_seq'::regclass);


--
-- Name: contest_problems id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest_problems ALTER COLUMN id SET DEFAULT nextval('public.contest_problems_id_seq'::regclass);


--
-- Name: contests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contests ALTER COLUMN id SET DEFAULT nextval('public.contests_id_seq'::regclass);


--
-- Name: problems id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.problems ALTER COLUMN id SET DEFAULT nextval('public.problems_id_seq'::regclass);


--
-- Name: submissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.submissions ALTER COLUMN id SET DEFAULT nextval('public.submissions_id_seq'::regclass);


--
-- Name: test_cases id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_cases ALTER COLUMN id SET DEFAULT nextval('public.test_cases_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: contest_participants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contest_participants (id, contest_id, user_id, joined_at) FROM stdin;
1	1	2	2026-06-19 06:19:05.117333+00
2	1	3	2026-06-20 04:21:00.073154+00
\.


--
-- Data for Name: contest_problems; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contest_problems (id, contest_id, problem_id, points) FROM stdin;
1	1	1	100
2	1	2	100
\.


--
-- Data for Name: contests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contests (id, title, description, invite_code, created_by, duration_minutes, starts_at, ends_at, is_public, created_at) FROM stdin;
1	First Contest		25QudTn8v08	2	5	2026-06-19 06:30:00+00	2026-06-19 06:35:00+00	f	2026-06-19 06:19:05.117333+00
\.


--
-- Data for Name: problems; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.problems (id, title, description, difficulty, created_at, category) FROM stdin;
1	Sum of Two Numbers	Read two integers from stdin and print their sum.\n\nInput format: two integers separated by a space\nOutput format: a single integer (the sum)	easy	2026-06-16 09:42:13.152299+00	\N
2	Maximum Sum Subarray of Size K	Given an array of N integers and an integer K, find the maximum sum of any contiguous subarray of size K.\n\nInput Format\nFirst line contains two integers N and K.\nSecond line contains N space-separated integers representing the array.\n\nOutput Format\nPrint a single integer, the maximum sum of any contiguous subarray of size K.\n\nConstraints\n1 ≤ K ≤ N ≤ 10^5\n-10^4 ≤ arr[i] ≤ 10^4	medium	2026-06-18 15:36:51.155503+00	Arrays
3	Maximum Equal 0s and 1s	Given a binary array containing only 0s and 1s, find the length of the longest contiguous subarray that contains an equal number of 0s and 1s.\n\nInput Format:\nThe first line contains an integer N, the size of the array.\nThe second line contains N space-separated integers (0 or 1).\n\nOutput Format:\nPrint a single integer representing the length of the longest contiguous subarray having an equal number of 0s and 1s.\n\nConstraints:\n1 <= N <= 100000\nArray elements are either 0 or 1.\n\nExample:\nInput:\n6\n0 1 0 1 1 0\n\nOutput:\n6\n\nExplanation:\nThe entire array contains three 0s and three 1s, so the answer is 6.	medium	2026-06-21 12:57:08.324292+00	Arrays, Hashing, Prefix Sum
\.


--
-- Data for Name: submissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.submissions (id, user_id, problem_id, language, code, status, verdict, runtime_ms, memory_kb, error_output, created_at, judged_at, ai_review) FROM stdin;
1	2	1	cpp	#include<iostream>\nusing namespacen std;\nint main()\n{\nint a,b;\ncin >> a >> b;\ncout << a+b;\n}	compile_error	compile_error	\N	\N	/tmp/tmpxybvee9k/solution.cpp:2:7: error: expected nested-name-specifier before ‘namespacen’\n    2 | using namespacen std;\n      |       ^~~~~~~~~~\n/tmp/tmpxybvee9k/solution.cpp: In function ‘int main()’:\n/tmp/tmpxybvee9k/solution.cpp:6:1: error: ‘cin’ was not declared in this scope; did you mean ‘std::cin’?\n    6 | cin >> a >> b;\n      | ^~~\n      | std::cin\nIn file included from /tmp/tmpxybvee9k/solution.cpp:1:\n/usr/include/c++/12/iostream:60:18: note: ‘std::cin’ declared here\n   60 |   extern istream cin;           /// Linked to standard input\n      |                  ^~~\n/tmp/tmpxybvee9k/solution.cpp:7:1: error: ‘cout’ was not declared in this scope; did you mean ‘std::cout’?\n    7 | cout << a+b;\n      | ^~~~\n      | std::cout\n/usr/include/c++/12/iostream:61:18: note: ‘std::cout’ declared here\n   61 |   extern ostream cout;          /// Linked to standard output\n      |                  ^~~~\n	2026-06-16 09:49:18.388246+00	2026-06-17 04:51:42.363917+00	\N
2	2	1	cpp	#include<iostream>\nusing namespace std;\n\nint main(){\n    int a, b;\n    cin >> a >> b;\n    cout << a + b;\n    return 0;\n}	accepted	accepted	89.87612649798393	\N	\N	2026-06-16 17:38:27.905344+00	2026-06-17 04:51:45.338826+00	\N
23	2	1	python	print(8)	accepted	accepted	98.13639899948612	\N	\N	2026-06-17 12:22:26.43484+00	2026-06-17 12:22:26.975116+00	\N
3	2	1	cpp	#include<iostream>\nusing namespace std;\n\nint main(){\n    int a, b;\n    cin >> a >> b;\n    cout << a + b;\n    return 0;\n}	accepted	accepted	2.428589388728142	\N	\N	2026-06-17 04:45:48.992513+00	2026-06-17 04:51:48.241605+00	\N
18	2	1	python	print(8)	accepted	accepted	105.56731838732958	\N	\N	2026-06-17 11:00:46.590739+00	2026-06-17 11:00:47.43573+00	\N
4	2	1	cpp	#include<iostream>\nusing namespace std;\n\nint main(){\n    int a, b;\n    cin >> a >> b;\n    cout << a + b;\n    return 0;\n}	accepted	accepted	87.56017033010721	\N	\N	2026-06-17 04:53:16.66701+00	2026-06-17 04:53:21.338037+00	\N
5	2	1	cpp	#include<iostream>\nusing namespace std;\nint main(){\n    cout << 999;\n    return 0;\n}	wrong_answer	wrong_answer	86.32597047835588	\N	\N	2026-06-17 04:54:16.664715+00	2026-06-17 04:54:20.137893+00	\N
6	2	1	cpp	#include<iostream>\nint main() {\n    cout << "broken"\n}	compile_error	compile_error	\N	\N	/tmp/tmp__o4ia0g/solution.cpp: In function ‘int main()’:\n/tmp/tmp__o4ia0g/solution.cpp:3:5: error: ‘cout’ was not declared in this scope; did you mean ‘std::cout’?\n    3 |     cout << "broken"\n      |     ^~~~\n      |     std::cout\nIn file included from /tmp/tmp__o4ia0g/solution.cpp:1:\n/usr/include/c++/12/iostream:61:18: note: ‘std::cout’ declared here\n   61 |   extern ostream cout;          /// Linked to standard output\n      |                  ^~~~\n	2026-06-17 04:54:30.310582+00	2026-06-17 04:54:34.844909+00	\N
19	2	1	python	print(7)	wrong_answer	wrong_answer	179.90328092128038	\N	\N	2026-06-17 11:01:06.477273+00	2026-06-17 11:01:07.028667+00	\N
7	1	1	cpp	#include<iostream>\nusing namespace std;\nint main(){\nint a,b;\ncin>>a>>b;\ncout<<a+b<,endl;\nreturn 0;\n}	compile_error	compile_error	\N	\N	/tmp/tmpp18zpcy0/solution.cpp: In function ‘int main()’:\n/tmp/tmpp18zpcy0/solution.cpp:6:11: error: expected primary-expression before ‘,’ token\n    6 | cout<<a+b<,endl;\n      |           ^\n	2026-06-17 05:00:46.819542+00	2026-06-17 05:00:50.241676+00	\N
8	1	1	cpp	#include<iostream>\nusing namespace std;\nint main(){\nint a,b;\ncin>>a>>b;\ncout<<a+b<<endl;\nreturn 0;\n}	accepted	accepted	2.1827025339007378	\N	\N	2026-06-17 05:01:01.727592+00	2026-06-17 05:01:05.239981+00	\N
9	1	1	python	a,b=input()\nprint(a+b)	runtime_error	runtime_error	101.76889086142182	\N	Traceback (most recent call last):\n  File "/tmp/tmprr4wrhfe/solution.py", line 1, in <module>\n    a,b=input()\n    ^^^\nValueError: too many values to unpack (expected 2)\n	2026-06-17 06:22:00.937879+00	2026-06-17 06:22:01.740471+00	\N
20	2	1	python	print(7)	wrong_answer	wrong_answer	106.32617957890034	\N	\N	2026-06-17 11:01:17.874738+00	2026-06-17 11:01:18.245576+00	\N
10	1	1	python	a,b=map(int,input().split())\nprint(a+b)	accepted	accepted	100.53143091499805	\N	\N	2026-06-17 06:23:19.806927+00	2026-06-17 06:23:20.742286+00	\N
24	2	1	python	print(8)	accepted	accepted	102.1358035504818	\N	\N	2026-06-17 17:09:41.79436+00	2026-06-17 17:09:42.462059+00	\N
21	4	1	python	print(8)	accepted	accepted	101.1624913662672	\N	\N	2026-06-17 11:05:29.397022+00	2026-06-17 11:05:29.740839+00	\N
17	2	1	python	print(8)	accepted	accepted	108.24627801775932	\N	\N	2026-06-17 11:00:03.242019+00	2026-06-17 12:10:23.819934+00	\N
31	2	2	cpp	#include<iostream>\n#include<vector>\nusing namespace std;\nint main()\n{\nint n,k;\ncin >> n >>k;\nvector<int>a(n);\nfor(int i=0;i<n;i++) cin >> a[i];\nint curr_sum=0;\nfor(int i=0;i<k;i++)\n{\ncurr_sum=curr_sum+a[i];\n}\nint max_sum=curr_sum;\nfor(int i=k;i<n;i++)\n{\ncurr_sum=curr_sum+a[i]-a[i-k];\nmax_sum=max(curr_sum,max_sum);\n}\ncout<<max_sum;\n}	accepted	accepted	90.92055540531874	\N	\N	2026-06-18 15:44:06.842319+00	2026-06-18 15:44:10.503062+00	\N
11	2	1	python	a,b=map(int,input().split())\nprint(a+b)	accepted	accepted	105.749087408185	\N	\N	2026-06-17 07:22:52.596526+00	2026-06-17 12:10:24.32616+00	\N
25	2	1	python	print(8)	accepted	accepted	101.66707169264555	\N	\N	2026-06-18 04:36:59.563023+00	2026-06-18 04:37:00.469324+00	\N
12	2	1	python	a,b=map(int,input().split())\nprint(a+b)	accepted	accepted	110.02679634839296	\N	\N	2026-06-17 07:23:04.023029+00	2026-06-17 12:10:24.92584+00	\N
13	2	1	python	print(8)	accepted	accepted	108.05513244122267	\N	\N	2026-06-17 07:24:46.17443+00	2026-06-17 12:10:25.428252+00	\N
14	2	1	python	print(8)	accepted	accepted	104.05046306550503	\N	\N	2026-06-17 07:25:17.827127+00	2026-06-17 12:10:26.019048+00	\N
26	3	1	python	print(8)	accepted	accepted	99.6709568426013	\N	\N	2026-06-18 05:11:55.670439+00	2026-06-18 05:11:56.26932+00	\N
15	2	1	python	print(8)	accepted	accepted	106.14516958594322	\N	\N	2026-06-17 10:41:00.063397+00	2026-06-17 12:10:26.523845+00	\N
16	2	1	python	print(8)	accepted	accepted	186.2330948933959	\N	\N	2026-06-17 10:50:32.430508+00	2026-06-17 12:10:27.113207+00	\N
32	2	1	python	print(8)	wrong_answer	wrong_answer	186.35123781859875	\N	\N	2026-06-18 16:03:11.637522+00	2026-06-18 16:03:12.196185+00	\N
22	2	1	python	print(8)	accepted	accepted	102.29162499308586	\N	\N	2026-06-17 12:11:56.068729+00	2026-06-17 12:11:56.418972+00	\N
27	2	1	python	print(8)	accepted	accepted	183.46802052110434	\N	\N	2026-06-18 10:58:00.921003+00	2026-06-18 10:58:01.54801+00	\N
35	2	1	python	print(8)	wrong_answer	wrong_answer	188.87849617749453	\N	\N	2026-06-21 01:28:45.386704+00	2026-06-21 01:28:46.102228+00	\N
28	2	1	python	print(8)	wrong_answer	wrong_answer	101.26449819654226	\N	\N	2026-06-18 10:58:07.094145+00	2026-06-18 10:58:07.649168+00	\N
33	2	1	python	print(8)	wrong_answer	wrong_answer	179.19884528964758	\N	\N	2026-06-20 16:34:32.739438+00	2026-06-20 16:34:33.96398+00	\N
29	2	1	python	print(8)	wrong_answer	wrong_answer	101.87732055783272	\N	\N	2026-06-18 11:43:05.990327+00	2026-06-18 11:43:06.492183+00	\N
30	2	1	python	print(8)	wrong_answer	wrong_answer	102.32684202492237	\N	\N	2026-06-18 12:11:55.00603+00	2026-06-18 12:11:55.568372+00	\N
34	2	1	python	print(8)	wrong_answer	wrong_answer	102.91856620460749	\N	\N	2026-06-20 16:34:40.47966+00	2026-06-20 16:34:41.063277+00	\N
36	2	1	python	print(8)	accepted	accepted	99.8600097373128	\N	\N	2026-06-21 01:58:05.941846+00	2026-06-21 01:58:06.495653+00	\N
37	2	1	python	print(8)	wrong_answer	wrong_answer	98.46459701657295	\N	\N	2026-06-21 01:58:12.805139+00	2026-06-21 01:58:13.302233+00	## Complexity\n*   **Time Complexity:** O(1) - The solution performs a constant number of operations (printing a fixed number).\n*   **Space Complexity:** O(1) - The solution uses a constant amount of memory.\n\n## What Went Wrong\nThe code always prints the number `8`, regardless of the input. The problem requires reading two integers from standard input and printing their sum. The student's code does not perform any input reading or calculation.\n\n**Counter-example:**\nIf the input is `5 3`, the expected output is `8`.\nHowever, the student's code will output `8`.\n\nIf the input is `10 20`, the expected output is `30`.\nHowever, the student's code will output `8`.\n\n## Improvements\n1.  **Read Input:** Use `input().split()` to read the two numbers from a single line.\n2.  **Convert to Integers:** Convert the read strings to integers using `map(int, ...)` or by calling `int()` on each element.\n3.  **Calculate and Print Sum:** Add the two integers and print the result.\n\n## Alternative Approach\nThe problem can be solved by using a loop if there were multiple pairs of numbers to sum. However, for a single pair, direct input reading and calculation is the most efficient. If the problem involved summing an arbitrary number of inputs until a sentinel value, a `while` loop would be appropriate.\n\n## Summary\nYou've correctly identified that constant time and space are good, and now the focus is on making your code dynamic to handle varying inputs!
38	2	2	cpp	#include<iostream>\n#include<vector>\nusing namespace std;\nint main()\n{\nint n,k;\ncin >> n >>k;\nvector<int>a(n);\nfor(int i=0;i<n;i++) cin >> a[i];\nint curr_sum=0;\nfor(int i=0;i<k;i++)\n{\ncurr_sum=curr_sum+a[i];\n}\nint max_sum=curr_sum;\nfor(int i=k;i<n;i++)\n{\ncurr_sum=curr_sum+a[i]-a[i-k];\nmax_sum=max(curr_sum,max_sum);\n}\ncout<<max_sum;\n}	accepted	accepted	2.0739026367664337	\N	\N	2026-06-21 01:59:59.697495+00	2026-06-21 02:00:03.198558+00	\N
43	1	1	python	a,b=map(int(input()))\nprint(a+b)	runtime_error	runtime_error	99.76737760007381	\N	Traceback (most recent call last):\n  File "/tmp/tmpxurq1blp/solution.py", line 1, in <module>\n    a,b=map(int(input()))\n            ^^^^^^^^^^^^\nValueError: invalid literal for int() with base 10: '3 5'\n	2026-06-21 04:29:52.556587+00	2026-06-21 04:29:52.929787+00	\N
39	2	2	cpp	#include<iostream>\n#include<vector>\nusing namespace std;\nint main()\n{\nint n,k;\ncin >> n >>k;\nvector<int>a(n);\nfor(int i=0;i<n;i++) cin >> a[i];\nint curr_sum=0;\nfor(int i=0;i<k;i++)\n{\ncurr_sum=curr_sum+a[i];\n}\nint max_sum=curr_sum;\nfor(int i=k;i<n;i++)\n{\ncurr_sum=curr_sum+a[i]-a[i-k];\nmax_sum=max(curr_sum,max_sum);\n}\ncout<<max_sum;\n}	accepted	accepted	2.422323450446129	\N	\N	2026-06-21 02:00:06.109406+00	2026-06-21 02:00:09.00475+00	## Complexity\n\n**Time Complexity:** O(N)\nThe code iterates through the array twice: once to calculate the initial sum of the first `k` elements (O(K)) and then again to slide the window across the rest of the array (O(N-K)). Since K ≤ N, the dominant factor is O(N).\n\n**Space Complexity:** O(N)\nA `std::vector` of size `N` is used to store the input array.\n\n## What Went Wrong\n\nTheir solution is correct! They effectively implemented the sliding window technique, which is the optimal approach for this problem. They correctly calculated the initial sum and then efficiently updated it by adding the new element and subtracting the outgoing element in each step.\n\n## Improvements\n\n1.  **Use `long long` for sums:** Given the constraints `-10^4 ≤ arr[i] ≤ 10^4` and `N ≤ 10^5`, the sum of a subarray of size `K` could exceed the capacity of a standard 32-bit `int` (approx. 2 * 10^9). Using `long long` for `curr_sum` and `max_sum` would prevent potential integer overflow.\n2.  **Add necessary headers:** While `iostream` and `vector` are included, the `max` function is used without including the `<algorithm>` header. Although it might compile in some environments due to implicit inclusion or compiler extensions, it's best practice to explicitly include `<algorithm>` for `std::max`.\n3.  **Consider `ios_base::sync_with_stdio(false); cin.tie(NULL);`:** For competitive programming, especially with large inputs, these lines at the beginning of `main` can significantly speed up I/O operations, though for this specific problem's constraints and runtime, it might not be strictly necessary for an Accepted verdict.\n\n## Alternative Approach\n\nAnother approach could involve pre-calculating prefix sums. A prefix sum array `P` where `P[i]` stores the sum of elements from index 0 to `i-1` can be computed in O(N) time. Then, the sum of any subarray from index `i` to `j` (inclusive) can be found in O(1) time using `P[j+1] - P[i]`. Iterating through all possible subarrays of size `K` using this prefix sum array would still result in an O(N) time complexity.\n\n## Summary\n\nThis is a clean and efficient implementation of the sliding window technique, demonstrating a strong understanding of the problem.
40	1	1	cpp	a,b=map(int.input())\nprint(a+b)	compile_error	compile_error	\N	\N	/tmp/tmp42h0vhkc/solution.cpp:1:1: error: ‘a’ does not name a type\n    1 | a,b=map(int.input())\n      | ^\n	2026-06-21 04:29:14.650099+00	2026-06-21 04:29:15.023046+00	\N
41	1	1	python	a,b=map(int.input())\nprint(a+b)	runtime_error	runtime_error	185.99312286823988	\N	Traceback (most recent call last):\n  File "/tmp/tmpdat_n3x8/solution.py", line 1, in <module>\n    a,b=map(int.input())\n            ^^^^^^^^^\nAttributeError: type object 'int' has no attribute 'input'\n	2026-06-21 04:29:33.542783+00	2026-06-21 04:29:34.128038+00	\N
44	1	1	python	a,b=map(int,input().split())\nprint(a+b)	accepted	accepted	97.78966940939426	\N	\N	2026-06-21 04:31:54.497223+00	2026-06-21 04:31:54.735232+00	\N
42	1	1	python	a,b=map(int(input()))\nprint(a+b)	runtime_error	runtime_error	98.77020679414272	\N	Traceback (most recent call last):\n  File "/tmp/tmpfmn5y7x8/solution.py", line 1, in <module>\n    a,b=map(int(input()))\n            ^^^^^^^^^^^^\nValueError: invalid literal for int() with base 10: '3 5'\n	2026-06-21 04:29:50.789712+00	2026-06-21 04:29:51.036754+00	\N
45	1	1	python	a,b=map(int,input().split())\nprint(a+b)	accepted	accepted	103.83004881441593	\N	\N	2026-06-21 04:32:03.931078+00	2026-06-21 04:32:04.437016+00	## Complexity\n\n*   **Time Complexity:** O(1). The program reads two integers, performs a single addition, and prints the result. These operations take constant time, regardless of the input values.\n*   **Space Complexity:** O(1). The program only uses a few variables to store the input numbers and their sum, requiring a constant amount of memory.\n\n## What Went Wrong\n\nYour solution is perfect for this problem! You correctly understood the input format, used `map` and `split` efficiently to parse the input, and performed the addition and output as required. This is a textbook example of solving this type of problem.\n\n## Improvements\n\n1.  **Variable Naming:** While `a` and `b` are acceptable for such a simple problem, for more complex scenarios, using descriptive variable names like `num1` and `num2` can improve readability.\n2.  **Error Handling (for more complex problems):** For competitive programming, this is usually not necessary for basic input types. However, in real-world applications, you might consider using a `try-except` block to handle potential `ValueError` exceptions if the input is not a valid integer.\n3.  **Direct Printing (minor):** You could technically print the result of the `map` operation directly: `print(sum(map(int, input().split())))`. This is a stylistic choice and doesn't change performance significantly.\n\n## Alternative Approach\n\nAnother way to read the input would be to read each number on a separate line using two separate `input()` calls and then convert them to integers. Alternatively, you could use string formatting to read the entire line and then parse it manually, although `map` and `split` are generally the most idiomatic and efficient Pythonic approach for this specific input format.\n\n## Summary\n\nYou've demonstrated a strong grasp of fundamental Python input/output and arithmetic operations, leading to a perfectly accepted and efficient solution.
\.


--
-- Data for Name: test_cases; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.test_cases (id, problem_id, stdin, expected, is_sample) FROM stdin;
1	1	3 5	8	1
2	1	6 7	13	0
3	2	6 3\n2 1 5 1 3 2	9	1
4	2	5 2\n4 2 1 7 8	15	1
5	2	7 4\n1 4 2 10 23 3 1	39	0
6	3	6\n0 1 0 1 1 0	6	1
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, username, email, password, created_at, is_admin, google_id, profile_picture, date_of_birth) FROM stdin;
4	Krish	krishjain070105@gmail.com	$2b$12$9dDJhkv7gh7lW1XLRhUi8.pw4ClTw0BdhMqNte258WcDiBxxOpfSG	2026-06-17 11:04:48.513014+00	f	\N	\N	\N
2	akarsh	akarshjain2006@gmail.com	$2b$12$7gxoSRM/wigb9joXLn/t1OcvTj0y/mtwa51NxTIX6UMgFyMAB5Zj2	2026-06-16 09:27:15.056175+00	t	111990762971003303369	\N	\N
1	vikash kumar	u24cs145@coed.svnit.ac.in	$2b$12$UCKNSaOAQhRa6EBkDWa7E./sLxxWZcZF7B/NM77YF1igFPzyvDcFK	2026-06-16 08:38:52.835393+00	f	111666273138520463835	\N	\N
3	jain	u24cs143@coed.svnit.ac.in	$2b$12$MLy7W3GAX7zE5b/gkYwR3.gtueZEXarDPNHekn5rEF8kd0/3PqCwG	2026-06-16 09:39:42.51118+00	f	114540731360365016765	\N	\N
\.


--
-- Name: contest_participants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.contest_participants_id_seq', 2, true);


--
-- Name: contest_problems_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.contest_problems_id_seq', 2, true);


--
-- Name: contests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.contests_id_seq', 1, true);


--
-- Name: problems_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.problems_id_seq', 3, true);


--
-- Name: submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.submissions_id_seq', 45, true);


--
-- Name: test_cases_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.test_cases_id_seq', 6, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 5, true);


--
-- Name: contest_participants contest_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest_participants
    ADD CONSTRAINT contest_participants_pkey PRIMARY KEY (id);


--
-- Name: contest_problems contest_problems_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest_problems
    ADD CONSTRAINT contest_problems_pkey PRIMARY KEY (id);


--
-- Name: contests contests_invite_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contests
    ADD CONSTRAINT contests_invite_code_key UNIQUE (invite_code);


--
-- Name: contests contests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contests
    ADD CONSTRAINT contests_pkey PRIMARY KEY (id);


--
-- Name: problems problems_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.problems
    ADD CONSTRAINT problems_pkey PRIMARY KEY (id);


--
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- Name: test_cases test_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_google_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_google_id_key UNIQUE (google_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_problems_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_problems_id ON public.problems USING btree (id);


--
-- Name: ix_submissions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_submissions_id ON public.submissions USING btree (id);


--
-- Name: ix_submissions_problem_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_submissions_problem_id ON public.submissions USING btree (problem_id);


--
-- Name: ix_submissions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_submissions_user_id ON public.submissions USING btree (user_id);


--
-- Name: ix_test_cases_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_test_cases_id ON public.test_cases USING btree (id);


--
-- Name: ix_test_cases_problem_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_test_cases_problem_id ON public.test_cases USING btree (problem_id);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- PostgreSQL database dump complete
--

\unrestrict mLiWvKSIS1wIjugIRno1X8BaODFTHp1rk9FfhpDtc6C2Y7eivmcosNsygVLRSNU

